from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Contact, Thread, Email, AuditLog
from app.schemas import ContactStatusPayload

router = APIRouter(prefix="/contacts", tags=["contacts"])


@router.get("/{email}")
async def get_contact_profile_endpoint(
    email: str,
    db: AsyncSession = Depends(get_db),
):
    contact = await db.scalar(select(Contact).where(Contact.email == email))
    if contact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "NOT_FOUND",
                "message": "Contact not found",
                "details": {"email": email},
            },
        )

    open_threads = await db.scalar(
        select(func.count(Thread.id))
        .where(Thread.sender_email == email, Thread.status == "Open")
    )

    recent_emails_result = await db.execute(
        select(Email)
        .where(Email.sender == email)
        .order_by(Email.timestamp.desc())
        .limit(10)
    )
    recent_emails = recent_emails_result.scalars().all()

    return {
        "contact": {
            "id": str(contact.id),
            "email": contact.email,
            "name": contact.name,
            "company": contact.company,
            "status": contact.status,
            "account_value": float(contact.account_value) if contact.account_value is not None else None,
            "churn_risk_score": contact.churn_risk_score,
            "created_at": contact.created_at.isoformat() if contact.created_at else None,
            "last_contact_at": contact.last_contact_at.isoformat() if contact.last_contact_at else None,
        },
        "open_thread_count": open_threads or 0,
        "recent_emails": [
            {
                "id": str(email.id),
                "message_id": email.message_id,
                "subject": email.subject,
                "timestamp": email.timestamp.isoformat(),
                "category": email.category,
                "urgency": email.urgency,
                "sentiment_score": email.sentiment_score,
                "status": email.status,
            }
            for email in recent_emails
        ],
        "churn_risk_score": contact.churn_risk_score,
    }


@router.patch("/{email}/status")
async def update_contact_status(
    email: str,
    payload: ContactStatusPayload,
    db: AsyncSession = Depends(get_db),
):
    contact = await db.scalar(select(Contact).where(Contact.email == email))
    if contact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "NOT_FOUND",
                "message": "Contact not found",
                "details": {"email": email},
            },
        )

    before = contact.status
    contact.status = payload.status

    audit = AuditLog(
        entity_type="contact",
        entity_id=contact.id,
        action="status_updated",
        performed_by="user",
        diff={"before": before, "after": payload.status},
    )
    db.add(audit)
    await db.commit()

    return {
        "ok": True,
        "email": contact.email,
        "status": contact.status,
    }
