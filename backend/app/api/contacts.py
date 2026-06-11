import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text

from app.database import get_db
from app.schemas import ContactStatusPayload
from app.auth import verify_api_key

router = APIRouter(prefix="/contacts", tags=["contacts"], dependencies=[Depends(verify_api_key)])


@router.get("/{email}")
async def get_contact_profile_endpoint(
    email: str,
    db=Depends(get_db),
):
    contact = (
        await db.execute(
            text(
                """
                SELECT id, email, name, company, status, account_value, churn_risk_score, created_at, last_contact_at
                FROM contacts WHERE email = :email
                """
            ),
            {"email": email},
        )
    ).fetchone()

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
        text("SELECT COUNT(id) FROM threads WHERE sender_email = :email AND status = 'Open'"),
        {"email": email},
    )

    recent_emails_result = await db.execute(
        text(
            """
            SELECT id, message_id, subject, timestamp, category, urgency, sentiment_score, status
            FROM emails WHERE sender = :email
            ORDER BY timestamp DESC LIMIT 10
            """
        ),
        {"email": email},
    )
    recent_emails = recent_emails_result.fetchall()

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
    db=Depends(get_db),
):
    contact = (
        await db.execute(
            text("SELECT id, email, status FROM contacts WHERE email = :email"),
            {"email": email},
        )
    ).fetchone()

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
    await db.execute(
        text("UPDATE contacts SET status = :status WHERE email = :email"),
        {"status": payload.status, "email": email},
    )

    audit_id = uuid.uuid4()
    await db.execute(
        text(
            """
            INSERT INTO audit_log (id, entity_type, entity_id, action, performed_by, timestamp, diff)
            VALUES (:id, :entity_type, :entity_id, :action, :performed_by, :timestamp, :diff)
            """
        ),
        {
            "id": audit_id,
            "entity_type": "contact",
            "entity_id": contact.id,
            "action": "status_updated",
            "performed_by": "user",
            "timestamp": datetime.now(timezone.utc),
            "diff": json.dumps({"before": before, "after": payload.status}),
        },
    )
    await db.commit()

    return {
        "ok": True,
        "email": contact.email,
        "status": payload.status,
    }

