from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Thread, Email, Action

router = APIRouter(prefix="/threads", tags=["threads"])


@router.get("")
async def get_all_threads(db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Thread)
        .options(
            joinedload(Thread.emails).joinedload(Email.actions)
        )
        .order_by(Thread.last_updated_at.desc())
    )
    result = await db.execute(stmt)
    threads = result.unique().scalars().all()

    response = []
    for thread in threads:
        sorted_emails = sorted(thread.emails, key=lambda e: e.timestamp)
        emails_list = []
        for email in sorted_emails:
            actions_list = [
                {
                    "id": str(action.id),
                    "action_type": action.action_type,
                    "proposed_content": action.proposed_content,
                    "is_approved": action.is_approved,
                    "approved_by": action.approved_by,
                    "executed_at": action.executed_at.isoformat() if action.executed_at else None,
                    "agent_reasoning_log": action.agent_reasoning_log,
                }
                for action in email.actions
            ]
            emails_list.append(
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
                    "raw_entities": email.raw_entities,
                    "status": email.status,
                    "actions": actions_list,
                }
            )
        response.append(
            {
                "id": str(thread.id),
                "thread_id": thread.thread_id,
                "subject": thread.subject,
                "sender_email": thread.sender_email,
                "first_seen_at": thread.first_seen_at.isoformat() if thread.first_seen_at else None,
                "last_updated_at": thread.last_updated_at.isoformat() if thread.last_updated_at else None,
                "status": thread.status,
                "assigned_to": thread.assigned_to,
                "emails": emails_list,
            }
        )
    return response


@router.get("/{contact_email}")
async def get_threads_by_contact(contact_email: str, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Thread)
        .where(Thread.sender_email == contact_email)
        .options(
            joinedload(Thread.emails).joinedload(Email.actions)
        )
        .order_by(Thread.last_updated_at.desc())
    )
    result = await db.execute(stmt)
    threads = result.unique().scalars().all()

    response = []
    for thread in threads:
        # Sort emails chronologically
        sorted_emails = sorted(thread.emails, key=lambda e: e.timestamp)
        emails_list = []
        for email in sorted_emails:
            actions_list = [
                {
                    "id": str(action.id),
                    "action_type": action.action_type,
                    "proposed_content": action.proposed_content,
                    "is_approved": action.is_approved,
                    "approved_by": action.approved_by,
                    "executed_at": action.executed_at.isoformat() if action.executed_at else None,
                    "agent_reasoning_log": action.agent_reasoning_log,
                }
                for action in email.actions
            ]
            emails_list.append(
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
                    "raw_entities": email.raw_entities,
                    "status": email.status,
                    "actions": actions_list,
                }
            )
        response.append(
            {
                "id": str(thread.id),
                "thread_id": thread.thread_id,
                "subject": thread.subject,
                "sender_email": thread.sender_email,
                "first_seen_at": thread.first_seen_at.isoformat() if thread.first_seen_at else None,
                "last_updated_at": thread.last_updated_at.isoformat() if thread.last_updated_at else None,
                "status": thread.status,
                "assigned_to": thread.assigned_to,
                "emails": emails_list,
            }
        )

    return response
