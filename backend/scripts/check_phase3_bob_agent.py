import asyncio
from datetime import datetime, timezone

from sentence_transformers import SentenceTransformer
from sqlalchemy import select

from app.config import settings
from app.database import get_db_session
from app.models import Action, Contact, Email, Thread
from app.services.agent import run


EXPECTED_SEQUENCE = [
    "get_thread_history",
    "search_knowledge_base",
    "check_account_status",
    "flag_for_legal",
    "draft_reply",
    "escalate_to_human",
]


async def main() -> None:
    embedder = SentenceTransformer(settings.embedding_model)
    async with get_db_session() as db:
        email = await _ensure_bob_email(db)
        result = await run(str(email.id), db, embedder, dry_run=False)
        stored = await db.get(Action, result["action_id"])
        steps = stored.agent_reasoning_log["steps"]
        sequence = [step["action"] for step in steps[:6]]
        print({"sequence": sequence, "stored_action_id": result["action_id"], "steps_taken": result["steps_taken"]})
        if sequence != EXPECTED_SEQUENCE:
            raise SystemExit(f"Unexpected sequence: {sequence}")


async def _ensure_bob_email(db):
    sender = "bob.jones@enterprise.net"
    contact = await db.scalar(select(Contact).where(Contact.email == sender))
    if contact is None:
        contact = Contact(
            email=sender,
            name="Bob Jones",
            company="Enterprise Net",
            status="VIP",
            account_value=150000,
            churn_risk_score=0.85,
        )
        db.add(contact)
        await db.flush()
    else:
        contact.status = "VIP"
        contact.account_value = 150000
        contact.churn_risk_score = 0.85

    thread = await db.scalar(select(Thread).where(Thread.thread_id == "thread_bob_outage"))
    timestamp = datetime(2023, 10, 19, 14, 0, tzinfo=timezone.utc)
    if thread is None:
        thread = Thread(
            thread_id="thread_bob_outage",
            subject="Escalation: SLA Breach + Legal Review",
            sender_email=sender,
            first_seen_at=timestamp,
            last_updated_at=timestamp,
        )
        db.add(thread)
        await db.flush()
    else:
        thread.sender_email = sender
        thread.status = "Open"
        thread.last_updated_at = timestamp

    email = await db.scalar(select(Email).where(Email.message_id == "msg_phase3_bob_outage"))
    if email is None:
        email = Email(
            thread_id=thread.id,
            message_id="msg_phase3_bob_outage",
            sender=sender,
            subject="Escalation: SLA Breach + Legal Review",
            body=(
                "We have reviewed the October 1st incident report you provided. The RCA is inadequate - "
                "it does not address the root cause or corrective actions. Our legal team is now involved. "
                "Please expect formal correspondence. We are also putting the renewal on hold pending resolution."
            ),
            timestamp=timestamp,
            category="Legal",
            urgency="High",
            requires_human=True,
            raw_entities={"is_spam": False, "is_security_threat": False},
            status="Received",
        )
        db.add(email)
        await db.flush()
    else:
        email.thread_id = thread.id
        email.sender = sender
        email.subject = "Escalation: SLA Breach + Legal Review"
        email.body = (
            "We have reviewed the October 1st incident report you provided. The RCA is inadequate - "
            "it does not address the root cause or corrective actions. Our legal team is now involved. "
            "Please expect formal correspondence. We are also putting the renewal on hold pending resolution."
        )
        email.timestamp = timestamp
        email.category = "Legal"
        email.urgency = "High"
        email.requires_human = True
        email.raw_entities = {"is_spam": False, "is_security_threat": False}
        email.status = "Received"

    await db.commit()
    return email


if __name__ == "__main__":
    asyncio.run(main())
