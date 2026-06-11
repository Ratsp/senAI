import asyncio
import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import text

from app.config import settings
from app.database import get_db_session
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
    try:
        from sentence_transformers import SentenceTransformer
        embedder = SentenceTransformer(settings.embedding_model)
    except Exception as exc:
        print(f"Warning: Failed to load SentenceTransformer: {exc}. Using DummyEmbedder fallback.")
        class DummyEmbedder:
            def encode(self, text: str):
                return [0.0] * 384
        embedder = DummyEmbedder()
    async with get_db_session() as db:
        email = await _ensure_bob_email(db)
        result = await run(str(email.id), db, embedder, dry_run=False)

        action_res = await db.execute(
            text("SELECT agent_reasoning_log FROM actions WHERE id = :id"),
            {"id": uuid.UUID(result["action_id"])},
        )
        stored = action_res.fetchone()
        log_data = stored.agent_reasoning_log
        if isinstance(log_data, str):
            log_data = json.loads(log_data)
        steps = log_data["steps"]
        sequence = [step["action"] for step in steps[:6]]
        print({"sequence": sequence, "stored_action_id": result["action_id"], "steps_taken": result["steps_taken"]})
        if sequence != EXPECTED_SEQUENCE:
            raise SystemExit(f"Unexpected sequence: {sequence}")


async def _ensure_bob_email(db):
    sender = "bob.jones@enterprise.net"
    contact_res = await db.execute(
        text("SELECT id, email, status, account_value, churn_risk_score FROM contacts WHERE email = :email"),
        {"email": sender},
    )
    contact = contact_res.fetchone()
    now = datetime.now(timezone.utc)
    if contact is None:
        contact_id = uuid.uuid4()
        await db.execute(
            text(
                """
                INSERT INTO contacts (id, email, name, company, status, account_value, churn_risk_score, created_at, last_contact_at)
                VALUES (:id, :email, 'Bob Jones', 'Enterprise Net', 'VIP', 150000.0, 0.85, :now, :now)
                """
            ),
            {"id": contact_id, "email": sender, "now": now},
        )
        contact_res = await db.execute(
            text("SELECT id, email, status, account_value, churn_risk_score FROM contacts WHERE email = :email"),
            {"email": sender},
        )
        contact = contact_res.fetchone()
    else:
        await db.execute(
            text("UPDATE contacts SET status = 'VIP', account_value = 150000.0, churn_risk_score = 0.85 WHERE id = :id"),
            {"id": contact.id},
        )

    thread_res = await db.execute(text("SELECT id, thread_id FROM threads WHERE thread_id = 'thread_bob_outage'"))
    thread = thread_res.fetchone()
    timestamp = datetime(2023, 10, 19, 14, 0, tzinfo=timezone.utc)
    if thread is None:
        thread_uuid = uuid.uuid4()
        await db.execute(
            text(
                """
                INSERT INTO threads (id, thread_id, subject, sender_email, first_seen_at, last_updated_at, status, assigned_to)
                VALUES (:id, 'thread_bob_outage', 'Escalation: SLA Breach + Legal Review', :sender, :first_seen, :last_seen, 'Open', NULL)
                """
            ),
            {"id": thread_uuid, "sender": sender, "first_seen": timestamp, "last_seen": timestamp},
        )
        thread_res = await db.execute(
            text("SELECT id, thread_id FROM threads WHERE thread_id = 'thread_bob_outage'")
        )
        thread = thread_res.fetchone()
    else:
        await db.execute(
            text(
                "UPDATE threads SET sender_email = :sender, status = 'Open', last_updated_at = :timestamp WHERE id = :id"
            ),
            {"sender": sender, "timestamp": timestamp, "id": thread.id},
        )

    email_res = await db.execute(text("SELECT id, message_id FROM emails WHERE message_id = 'msg_phase3_bob_outage'"))
    email = email_res.fetchone()
    body_text = (
        "We have reviewed the October 1st incident report you provided. The RCA is inadequate - "
        "it does not address the root cause or corrective actions. Our legal team is now involved. "
        "Please expect formal correspondence. We are also putting the renewal on hold pending resolution."
    )
    if email is None:
        email_uuid = uuid.uuid4()
        await db.execute(
            text(
                """
                INSERT INTO emails (id, thread_id, message_id, sender, subject, body, timestamp, category, urgency, requires_human, raw_entities, status)
                VALUES (:id, :thread_id, 'msg_phase3_bob_outage', :sender, 'Escalation: SLA Breach + Legal Review', :body, :timestamp, 'Legal', 'High', TRUE, :raw_entities, 'Received')
                """
            ),
            {
                "id": email_uuid,
                "thread_id": thread.id,
                "sender": sender,
                "body": body_text,
                "timestamp": timestamp,
                "raw_entities": json.dumps({"is_spam": False, "is_security_threat": False}),
            },
        )
        email_res = await db.execute(
            text("SELECT id, message_id FROM emails WHERE message_id = 'msg_phase3_bob_outage'")
        )
        email = email_res.fetchone()
    else:
        await db.execute(
            text(
                """
                UPDATE emails
                SET thread_id = :thread_id, sender = :sender, subject = 'Escalation: SLA Breach + Legal Review',
                    body = :body, timestamp = :timestamp, category = 'Legal', urgency = 'High',
                    requires_human = TRUE, raw_entities = :raw_entities, status = 'Received'
                WHERE id = :id
                """
            ),
            {
                "thread_id": thread.id,
                "sender": sender,
                "body": body_text,
                "timestamp": timestamp,
                "raw_entities": json.dumps({"is_spam": False, "is_security_threat": False}),
                "id": email.id,
            },
        )

    await db.commit()
    return email


if __name__ == "__main__":
    asyncio.run(main())
