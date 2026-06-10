from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Action, AuditLog, Email
from app.schemas import RespondPayload
from app.services.agent_tools import escalate_to_human

router = APIRouter(prefix="/respond", tags=["respond"])


@router.post("/{email_id}")
async def respond_to_email(
    email_id: str,
    payload: RespondPayload,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    # Try converting email_id to UUID to confirm format
    try:
        email_uuid = UUID(email_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "VALIDATION_ERROR",
                "message": "Invalid email ID format",
                "details": {"email_id": "Must be a valid UUID"},
            },
        )

    email = await db.get(Email, email_uuid)
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "NOT_FOUND",
                "message": "Email not found",
                "details": {"email_id": email_id},
            },
        )

    ws_manager = request.app.state.ws_manager

    if payload.escalate:
        res = await escalate_to_human(
            email_id=str(email.id),
            reason=payload.reply_text or "Human initiated escalation",
            priority="High",
            db=db,
        )
        if not res.get("ok"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error_code": "PROCESSING_ERROR",
                    "message": "Failed to escalate email",
                    "details": res,
                },
            )
        # Broadcast escalation event to WebSocket
        await ws_manager.broadcast(
            {
                "type": "agent_decision",
                "event": "agent_decision",
                "email_id": str(email.id),
                "action_type": "Escalate",
                "status": "Escalated",
                "reason": payload.reply_text or "Human initiated escalation",
            }
        )
        return res
    else:
        # Create approved Action
        action = Action(
            email_id=email.id,
            action_type="Auto-Reply",
            proposed_content=payload.reply_text,
            is_approved=True,
            approved_by="user",
            executed_at=datetime.now(timezone.utc),
        )
        db.add(action)

        email.status = "Replied"

        audit = AuditLog(
            entity_type="email",
            entity_id=email.id,
            action="manual_reply_sent",
            performed_by="user",
            diff={"reply_text": payload.reply_text},
        )
        db.add(audit)

        await db.commit()

        # Broadcast agent_decision event to WebSocket
        await ws_manager.broadcast(
            {
                "type": "agent_decision",
                "event": "agent_decision",
                "email_id": str(email.id),
                "action_type": "Auto-Reply",
                "status": "Replied",
                "reply_text": payload.reply_text,
            }
        )

        return {
            "ok": True,
            "email_id": str(email.id),
            "action_id": str(action.id),
            "status": "Replied",
        }
