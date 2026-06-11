import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text

from app.database import get_db

router = APIRouter(prefix="/threads", tags=["threads"])


async def _fetch_thread_hierarchy(db, contact_email: str | None = None):
    # Fetch threads
    if contact_email:
        res = await db.execute(
            text(
                """
                SELECT id, thread_id, subject, sender_email, first_seen_at, last_updated_at, status, assigned_to
                FROM threads
                WHERE sender_email = :contact_email
                ORDER BY last_updated_at DESC
                """
            ),
            {"contact_email": contact_email},
        )
    else:
        res = await db.execute(
            text(
                """
                SELECT id, thread_id, subject, sender_email, first_seen_at, last_updated_at, status, assigned_to
                FROM threads
                ORDER BY last_updated_at DESC
                """
            )
        )
    threads = res.fetchall()

    if not threads:
        return []

    thread_ids = [t.id for t in threads]

    # Fetch emails
    email_res = await db.execute(
        text(
            """
            SELECT id, thread_id, message_id, sender, subject, body, timestamp, sentiment_score, category, urgency, requires_human, confidence, raw_entities, status
            FROM emails
            WHERE thread_id = ANY(:thread_ids)
            ORDER BY timestamp ASC
            """
        ),
        {"thread_ids": thread_ids},
    )
    emails = email_res.fetchall()

    if not emails:
        return [
            {
                "id": str(t.id),
                "thread_id": t.thread_id,
                "subject": t.subject,
                "sender_email": t.sender_email,
                "first_seen_at": t.first_seen_at.isoformat() if t.first_seen_at else None,
                "last_updated_at": t.last_updated_at.isoformat() if t.last_updated_at else None,
                "status": t.status,
                "assigned_to": t.assigned_to,
                "emails": [],
            }
            for t in threads
        ]

    email_ids = [e.id for e in emails]

    # Fetch actions
    action_res = await db.execute(
        text(
            """
            SELECT id, email_id, action_type, proposed_content, is_approved, approved_by, executed_at, agent_reasoning_log
            FROM actions
            WHERE email_id = ANY(:email_ids)
            ORDER BY 
              CASE WHEN jsonb_exists(agent_reasoning_log, 'steps') OR jsonb_exists(agent_reasoning_log, 'react_agent') THEN 0 ELSE 1 END,
              executed_at DESC NULLS LAST
            """
        ),
        {"email_ids": email_ids},
    )
    actions = action_res.fetchall()

    # Map actions to emails
    actions_by_email = {}
    for action in actions:
        email_uuid = action.email_id
        if email_uuid not in actions_by_email:
            actions_by_email[email_uuid] = []
        actions_by_email[email_uuid].append(
            {
                "id": str(action.id),
                "action_type": action.action_type,
                "proposed_content": action.proposed_content,
                "is_approved": action.is_approved,
                "approved_by": action.approved_by,
                "executed_at": action.executed_at.isoformat() if action.executed_at else None,
                "agent_reasoning_log": action.agent_reasoning_log,
            }
        )

    # Map emails to threads
    emails_by_thread = {}
    for email in emails:
        thread_uuid = email.thread_id
        if thread_uuid not in emails_by_thread:
            emails_by_thread[thread_uuid] = []

        raw_ent = email.raw_entities
        if isinstance(raw_ent, str):
            try:
                raw_ent = json.loads(raw_ent)
            except Exception:
                pass

        emails_by_thread[thread_uuid].append(
            {
                "id": str(email.id),
                "message_id": email.message_id,
                "sender": email.sender,
                "subject": email.subject,
                "body": email.body,
                "timestamp": email.timestamp.isoformat(),
                "sentiment_score": email.sentiment_score,
                "category": email.category,
                "urgency": email.urgency,
                "requires_human": email.requires_human,
                "confidence": email.confidence,
                "raw_entities": raw_ent,
                "status": email.status,
                "actions": actions_by_email.get(email.id, []),
            }
        )

    # Construct final hierarchy
    response = []
    for t in threads:
        response.append(
            {
                "id": str(t.id),
                "thread_id": t.thread_id,
                "subject": t.subject,
                "sender_email": t.sender_email,
                "first_seen_at": t.first_seen_at.isoformat() if t.first_seen_at else None,
                "last_updated_at": t.last_updated_at.isoformat() if t.last_updated_at else None,
                "status": t.status,
                "assigned_to": t.assigned_to,
                "emails": emails_by_thread.get(t.id, []),
            }
        )
    return response


@router.get("")
async def get_all_threads(db=Depends(get_db)):
    return await _fetch_thread_hierarchy(db)


@router.get("/{contact_email}")
async def get_threads_by_contact(contact_email: str, db=Depends(get_db)):
    return await _fetch_thread_hierarchy(db, contact_email)

