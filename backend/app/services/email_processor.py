import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import text

from app.database import get_db_session
from app.services.llm_classifier import classify_email
from app.services.rag_pipeline import retrieve_relevant_chunks
from app.services.agent import run as run_agent
from app.services.sentiment_tracker import detect_deterioration
from app.websocket.manager import ConnectionManager


class SimpleEmail:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


SEMAPHORE = asyncio.Semaphore(15)
logger = logging.getLogger("email_processor")


async def process_email_job(
    job_id: str,
    email_id: UUID,
    jobs: dict,
    manager: ConnectionManager,
    embedder: Any,
) -> None:
    jobs[job_id]["status"] = "processing"
    async with SEMAPHORE:
        await _process_email_job_impl(job_id, email_id, jobs, manager, embedder)


async def _process_email_job_impl(
    job_id: str,
    email_id: UUID,
    jobs: dict,
    manager: ConnectionManager,
    embedder: Any,
) -> None:
    try:
        async with get_db_session() as session:
            email_res = await session.execute(
                text(
                    """
                    SELECT id, message_id, thread_id, sender, subject, body, timestamp, sentiment_score, category, urgency, requires_human, confidence, raw_entities, status
                    FROM emails WHERE id = :id
                    """
                ),
                {"id": email_id},
            )
            row = email_res.fetchone()
            if row is None:
                raise ValueError(f"Email {email_id} was not found")

            email = SimpleEmail(**dict(row._mapping))
            email.status = "Processing"

            await session.execute(
                text("UPDATE emails SET status = 'Processing' WHERE id = :id"),
                {"id": email.id},
            )
            await session.commit()

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

            raw_ent = email.raw_entities
            if isinstance(raw_ent, str):
                try:
                    raw_ent = json.loads(raw_ent)
                except Exception:
                    raw_ent = {}
            elif raw_ent is None:
                raw_ent = {}

            email.raw_entities = {
                **raw_ent,
                "detected_entities": classification.get("detected_entities", {}),
                "sentiment": classification.get("sentiment"),
                "escalation_reason": classification.get("escalation_reason"),
                "rag_sources": [chunk["source_doc"] for chunk in rag_chunks],
            }

            await session.execute(
                text(
                    """
                    UPDATE emails
                    SET category = :category, urgency = :urgency, requires_human = :requires_human,
                        confidence = :confidence, sentiment_score = :sentiment_score, raw_entities = :raw_entities
                    WHERE id = :id
                    """
                ),
                {
                    "category": email.category,
                    "urgency": email.urgency,
                    "requires_human": email.requires_human,
                    "confidence": email.confidence,
                    "sentiment_score": email.sentiment_score,
                    "raw_entities": json.dumps(email.raw_entities),
                    "id": email.id,
                },
            )
            # Save classification updates
            await session.commit()

            # 1. Broadcast new_email event
            await manager.broadcast(
                {
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
                    },
                }
            )

            # 2. Run the ReAct agent loop
            agent_skipped = False
            skip_reason = None

            from app.services.heuristic_filter import SPAM_KEYWORDS, SPAM_DOMAINS, _domain, _contains_any
            text_content = f"{email.subject or ''}\n{email.body or ''}".lower()
            is_spam_by_keyword = _contains_any(text_content, SPAM_KEYWORDS)
            is_spam_by_domain = _domain(email.sender) in SPAM_DOMAINS

            if email.category == "Spam":
                agent_skipped = True
                skip_reason = "Email classified as Spam"
            elif is_spam_by_keyword:
                agent_skipped = True
                skip_reason = "Email contains spam keywords (blocklisted)"
            elif is_spam_by_domain:
                agent_skipped = True
                skip_reason = "Email sender domain is blocklisted"

            run_agent_decision = "Skipped" if agent_skipped else "Executed"
            log_payload = {
                "email_id": str(email.id),
                "classification": email.category,
                "confidence": email.confidence,
                "requires_human": email.requires_human,
                "run_agent_decision": run_agent_decision,
                "skip_reason": skip_reason,
            }
            logger.info("Structured agent execution log: %s", json.dumps(log_payload))
            print(f"STRUCTURED_LOG: {json.dumps(log_payload)}", flush=True)

            if agent_skipped:
                email.raw_entities["AGENT_EXECUTION_STATUS"] = "Skipped"
                email.raw_entities["AGENT_EXECUTION_SKIP_REASON"] = skip_reason
                
                await session.execute(
                    text("UPDATE emails SET raw_entities = :raw_entities, status = 'Ignored' WHERE id = :id"),
                    {
                        "raw_entities": json.dumps(email.raw_entities),
                        "id": email.id,
                    },
                )
                await session.commit()

                # Broadcast decision with "Ignored"
                await manager.broadcast(
                    {
                        "type": "agent_decision",
                        "email_id": str(email.id),
                        "action_type": "Ignored",
                        "reasoning_summary": f"Agent skipped: {skip_reason}",
                    }
                )
                action_type = "Ignored"
                email_status = "Ignored"
            else:
                email.raw_entities["AGENT_EXECUTION_STATUS"] = "Executed"
                await session.execute(
                    text("UPDATE emails SET raw_entities = :raw_entities WHERE id = :id"),
                    {
                        "raw_entities": json.dumps(email.raw_entities),
                        "id": email.id,
                    },
                )
                await session.commit()

                try:
                    agent_result = await run_agent(str(email.id), session, embedder)

                    # Extract reasoning summary
                    steps = agent_result.get("reasoning_log", [])
                    reasoning_summary = " | ".join(f"{s.get('action')}: {s.get('thought')}" for s in steps)

                    # Fetch action type
                    action_id = agent_result.get("action_id")
                    action = None
                    if action_id:
                        action_res = await session.execute(
                            text("SELECT action_type FROM actions WHERE id = :id"),
                            {"id": UUID(action_id)},
                        )
                        action = action_res.fetchone()
                    action_type = action.action_type if action else "Ignored"
                    
                    # Refresh email status from DB since agent may have updated it (e.g. to Escalated, Replied)
                    fresh_email = (await session.execute(
                        text("SELECT status FROM emails WHERE id = :id"),
                        {"id": email.id}
                    )).fetchone()
                    email_status = fresh_email.status if fresh_email else "Processed"

                    # 3. Broadcast agent_decision event
                    await manager.broadcast(
                        {
                            "type": "agent_decision",
                            "email_id": str(email.id),
                            "action_type": action_type,
                            "reasoning_summary": reasoning_summary,
                        }
                    )
                except Exception as agent_exc:
                    email.raw_entities["AGENT_EXECUTION_STATUS"] = "Failed"
                    email.raw_entities["AGENT_EXECUTION_ERROR"] = str(agent_exc)
                    await session.execute(
                        text("UPDATE emails SET raw_entities = :raw_entities, status = 'Failed' WHERE id = :id"),
                        {
                            "raw_entities": json.dumps(email.raw_entities),
                            "id": email.id,
                        },
                    )
                    await session.commit()
                    raise

            # 4. Check if contact sentiment has deteriorated
            if await detect_deterioration(email.sender, session):
                contact_res = await session.execute(
                    text("SELECT id, status, churn_risk_score FROM contacts WHERE email = :email"),
                    {"email": email.sender},
                )
                contact = contact_res.fetchone()
                if contact:
                    new_churn_risk_score = min(1.0, (contact.churn_risk_score or 0.0) + 0.2)
                    
                    from app.config import settings
                    from datetime import timedelta
                    cutoff = datetime.now(timezone.utc) - timedelta(hours=settings.unresolved_risk_hours)
                    
                    unresolved_count = await session.scalar(
                        text("""
                            SELECT COUNT(id) FROM threads
                            WHERE sender_email = :email
                              AND status = 'Open'
                              AND first_seen_at < :cutoff
                        """),
                        {"email": email.sender, "cutoff": cutoff}
                    )
                    
                    should_mark_at_risk = int(unresolved_count or 0) > 0
                    new_status = "At Risk" if should_mark_at_risk else contact.status
                    
                    await session.execute(
                        text("UPDATE contacts SET churn_risk_score = :churn, status = :status WHERE id = :id"),
                        {"churn": new_churn_risk_score, "status": new_status, "id": contact.id},
                    )

                    audit_id = uuid.uuid4()
                    audit_diff = {"churn_risk_score": new_churn_risk_score}
                    if should_mark_at_risk and contact.status != "At Risk":
                        audit_diff["status"] = {"before": contact.status, "after": "At Risk"}
                        
                    await session.execute(
                        text(
                            """
                            INSERT INTO audit_log (id, entity_type, entity_id, action, performed_by, timestamp, diff)
                            VALUES (:id, 'contact', :entity_id, 'churn_risk_increased', 'system', :timestamp, :diff)
                            """
                        ),
                        {
                            "id": audit_id,
                            "entity_id": contact.id,
                            "timestamp": datetime.now(timezone.utc),
                            "diff": json.dumps(audit_diff),
                        },
                    )
                    await session.commit()

                # Broadcast sentiment alerts
                await manager.broadcast(
                    {
                        "type": "alert",
                        "alert_type": "sentiment_deterioration",
                        "email": email.sender,
                        "message": f"Sentiment deterioration alert for {email.sender}",
                    }
                )

            result = {"email_id": str(email.id), "action_type": action_type, "email_status": email_status}
            jobs[job_id].update({"status": "completed", "result": result})
            await manager.broadcast({"type": "job_completed", "job_id": job_id, "result": result})
    except Exception as exc:
        try:
            async with get_db_session() as fail_session:
                row_res = await fail_session.execute(
                    text("SELECT raw_entities FROM emails WHERE id = :id"),
                    {"id": email_id},
                )
                row = row_res.fetchone()
                if row:
                    raw_ent = row.raw_entities
                    if isinstance(raw_ent, str):
                        try:
                            raw_ent = json.loads(raw_ent)
                        except:
                            raw_ent = {}
                    elif raw_ent is None:
                        raw_ent = {}
                    raw_ent["AGENT_EXECUTION_STATUS"] = "Failed"
                    raw_ent["AGENT_EXECUTION_ERROR"] = str(exc)
                    await fail_session.execute(
                        text("UPDATE emails SET status = 'Failed', raw_entities = :raw_entities WHERE id = :id"),
                        {"raw_entities": json.dumps(raw_ent), "id": email_id},
                    )
                    await fail_session.commit()
        except Exception as inner_exc:
            print(f"Failed to record failure status for email {email_id}: {inner_exc}")
            
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


async def _load_thread_history(session, email) -> list[SimpleEmail]:
    result = await session.execute(
        text(
            """
            SELECT id, message_id, thread_id, sender, subject, body, timestamp, sentiment_score, category, urgency, requires_human, confidence, raw_entities, status
            FROM emails
            WHERE thread_id = :thread_id
            ORDER BY timestamp ASC
            """
        ),
        {"thread_id": email.thread_id},
    )
    return [SimpleEmail(**dict(row._mapping)) for row in result.fetchall()]


def _email_query(email) -> str:
    return f"{email.subject or ''}\n{email.body or ''}".strip()

