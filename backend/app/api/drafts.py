from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Action, AuditLog, Email
from app.schemas import DraftUpdatePayload

router = APIRouter(prefix="/drafts", tags=["drafts"])


@router.patch("/{id}")
async def update_draft(
    id: str,
    payload: DraftUpdatePayload,
    db: AsyncSession = Depends(get_db),
):
    try:
        action_uuid = UUID(id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "VALIDATION_ERROR",
                "message": "Invalid draft ID format",
                "details": {"id": "Must be a valid UUID"},
            },
        )

    action = await db.get(Action, action_uuid)
    if action is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "NOT_FOUND",
                "message": "Draft action not found",
                "details": {"id": id},
            },
        )

    before = action.proposed_content
    action.proposed_content = payload.proposed_content

    audit = AuditLog(
        entity_type="action",
        entity_id=action.id,
        action="draft_updated",
        performed_by="user",
        diff={"before": before, "after": payload.proposed_content},
    )
    db.add(audit)
    await db.commit()

    return {
        "ok": True,
        "id": str(action.id),
        "proposed_content": action.proposed_content,
    }


@router.post("/{id}/approve")
async def approve_draft(
    id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    try:
        action_uuid = UUID(id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "VALIDATION_ERROR",
                "message": "Invalid draft ID format",
                "details": {"id": "Must be a valid UUID"},
            },
        )

    action = await db.get(Action, action_uuid)
    if action is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "NOT_FOUND",
                "message": "Draft action not found",
                "details": {"id": id},
            },
        )

    action.is_approved = True
    action.executed_at = datetime.now(timezone.utc)
    action.approved_by = "user"

    email_uuid = action.email_id
    email = None
    if email_uuid:
        email = await db.get(Email, email_uuid)
        if email:
            email.status = "Replied"

    audit = AuditLog(
        entity_type="action",
        entity_id=action.id,
        action="draft_approved",
        performed_by="user",
        diff={"email_id": str(email_uuid) if email_uuid else None},
    )
    db.add(audit)
    await db.commit()

    # Broadcast WebSocket event
    ws_manager = request.app.state.ws_manager
    await ws_manager.broadcast(
        {
            "type": "draft_approved",
            "event": "draft_approved",
            "action_id": str(action.id),
            "email_id": str(email_uuid) if email_uuid else None,
            "status": "Replied",
        }
    )

    return {
        "ok": True,
        "action_id": str(action.id),
        "email_id": str(email_uuid) if email_uuid else None,
        "status": "Replied",
    }
