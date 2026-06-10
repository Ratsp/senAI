from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.database import get_db_session
from app.models import Action, AuditLog, Email, Contact
from app.services.llm_classifier import classify_email
from app.services.rag_pipeline import retrieve_relevant_chunks
from app.services.agent import run as run_agent
from app.services.sentiment_tracker import detect_deterioration
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
            # Save classification updates
            await session.commit()

            # 1. Broadcast new_email event
            await manager.broadcast({
                "type": "new_email",
                "email": {
                    "id": str(email.id),
                    "message_id": email.message_id,
                    "thread_id": str(email.thread_id),
                    "sender": email.sender,
                    "subject": email.subject,
                    "timestamp": email.timestamp.isoformat(),
                    "category": email.category,
                    "urgency": email.urgency,
                    "sentiment_score": email.sentiment_score,
                    "status": email.status,
                }
            })

            # 2. Run the ReAct agent loop
            agent_result = await run_agent(str(email.id), session, embedder)

            # Extract reasoning summary
            steps = agent_result.get("reasoning_log", [])
            reasoning_summary = " | ".join(f"{s.get('action')}: {s.get('thought')}" for s in steps)

            # Fetch action type
            action_id = agent_result.get("action_id")
            action = None
            if action_id:
                action = await session.get(Action, UUID(action_id))
            action_type = action.action_type if action else "Ignored"
            email_status = email.status

            # 3. Broadcast agent_decision event
            await manager.broadcast({
                "type": "agent_decision",
                "email_id": str(email.id),
                "action_type": action_type,
                "reasoning_summary": reasoning_summary,
            })

            # 4. Check if contact sentiment has deteriorated
            if await detect_deterioration(email.sender, session):
                contact = await session.scalar(select(Contact).where(Contact.email == email.sender))
                if contact:
                    contact.churn_risk_score = min(1.0, (contact.churn_risk_score or 0.0) + 0.2)
                    session.add(AuditLog(
                        entity_type="contact",
                        entity_id=contact.id,
                        action="churn_risk_increased",
                        performed_by="system",
                        diff={"churn_risk_score": contact.churn_risk_score}
                    ))
                    await session.commit()

                # Broadcast sentiment alerts
                await manager.broadcast({
                    "type": "alert",
                    "alert_type": "sentiment_deterioration",
                    "email": email.sender,
                    "message": f"Sentiment deterioration alert for {email.sender}",
                })

            result = {"email_id": str(email.id), "action_type": action_type, "email_status": email_status}
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
