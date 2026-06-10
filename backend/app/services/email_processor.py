from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.database import get_db_session
from app.models import Action, AuditLog, Email
from app.services.llm_classifier import classify_email
from app.services.rag_pipeline import retrieve_relevant_chunks
from app.websocket.manager import ConnectionManager


async def process_email_job(
    job_id: str,
    email_id: UUID,
    jobs: dict,
    manager: ConnectionManager,
    embedder: Any,
) -> None:
    jobs[job_id]["status"] = "processing"
    try:
        async with get_db_session() as session:
            email = await session.get(Email, email_id)
            if email is None:
                raise ValueError(f"Email {email_id} was not found")

            email.status = "Processing"
            rag_error = None
            thread_history = await _load_thread_history(session, email)
            try:
                rag_chunks = await retrieve_relevant_chunks(_email_query(email), embedder, session, top_k=3)
            except Exception as exc:
                rag_chunks = []
                rag_error = str(exc)

            classification = await classify_email(email, thread_history, rag_chunks)
            email.category = classification.get("category") or email.category
            email.urgency = classification.get("urgency") or email.urgency
            email.requires_human = bool(classification.get("requires_human", email.requires_human))
            email.confidence = classification.get("confidence")
            email.sentiment_score = classification.get("sentiment_score")
            email.raw_entities = {
                **(email.raw_entities or {}),
                "detected_entities": classification.get("detected_entities", {}),
                "sentiment": classification.get("sentiment"),
                "escalation_reason": classification.get("escalation_reason"),
            }

            action_type = _choose_action_type(email.requires_human, email.category, email.urgency)
            proposed_content = classification.get("suggested_reply") if action_type == "Auto-Reply" else None

            action = Action(
                email_id=email.id,
                action_type=action_type,
                proposed_content=proposed_content,
                agent_reasoning_log={
                    "classification_source": "groq_rag",
                    "category": email.category,
                    "urgency": email.urgency,
                    "requires_human": email.requires_human,
                    "confidence": email.confidence,
                    "rag_sources": [chunk["source_doc"] for chunk in rag_chunks],
                    "rag_error": rag_error,
                    "escalation_reason": classification.get("escalation_reason"),
                },
                is_approved=False,
            )
            email.status = "Escalated" if action_type in {"Escalate", "Legal-Flag"} else "Replied"
            audit = AuditLog(
                entity_type="email",
                entity_id=email.id,
                action="agent_processed",
                performed_by="system",
                diff={"action_type": action_type, "email_status": email.status},
            )
            session.add_all([action, audit])
            await session.commit()

            result = {"email_id": str(email.id), "action_type": action_type, "email_status": email.status}
            jobs[job_id].update({"status": "completed", "result": result})
            await manager.broadcast({"type": "job_completed", "job_id": job_id, "result": result})
    except Exception as exc:
        jobs[job_id].update({"status": "failed", "detail": str(exc)})
        await manager.broadcast({"type": "job_failed", "job_id": job_id, "detail": str(exc)})


def _choose_action_type(requires_human: bool, category: str | None, urgency: str | None) -> str:
    if category in {"Compliance", "Legal"}:
        return "Legal-Flag"
    if requires_human or urgency == "Critical":
        return "Escalate"
    if category == "Spam":
        return "Ignored"
    return "Auto-Reply"


async def _load_thread_history(session, email: Email) -> list[Email]:
    result = await session.execute(
        select(Email)
        .where(Email.thread_id == email.thread_id)
        .order_by(Email.timestamp.asc())
    )
    return list(result.scalars().all())


def _email_query(email: Email) -> str:
    return f"{email.subject or ''}\n{email.body or ''}".strip()
