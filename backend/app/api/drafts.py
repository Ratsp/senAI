import json
import uuid
from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import text

from app.database import get_db
from app.schemas import DraftUpdatePayload

router = APIRouter(prefix="/drafts", tags=["drafts"])


@router.patch("/{id}")
async def update_draft(
    id: str,
    payload: DraftUpdatePayload,
    db=Depends(get_db),
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

    action = (
        await db.execute(
            text("SELECT id, proposed_content FROM actions WHERE id = :id"),
            {"id": action_uuid},
        )
    ).fetchone()

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
    await db.execute(
        text("UPDATE actions SET proposed_content = :proposed_content WHERE id = :id"),
        {"proposed_content": payload.proposed_content, "id": action_uuid},
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
            "entity_type": "action",
            "entity_id": action.id,
            "action": "draft_updated",
            "performed_by": "user",
            "timestamp": datetime.now(timezone.utc),
            "diff": json.dumps({"before": before, "after": payload.proposed_content}),
        },
    )
    await db.commit()

    return {
        "ok": True,
        "id": str(action.id),
        "proposed_content": payload.proposed_content,
    }


@router.post("/{id}/approve")
async def approve_draft(
    id: str,
    request: Request,
    db=Depends(get_db),
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

    action = (
        await db.execute(
            text("SELECT id, email_id FROM actions WHERE id = :id"),
            {"id": action_uuid},
        )
    ).fetchone()

    if action is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "NOT_FOUND",
                "message": "Draft action not found",
                "details": {"id": id},
            },
        )

    now = datetime.now(timezone.utc)
    await db.execute(
        text(
            """
            UPDATE actions
            SET is_approved = TRUE, executed_at = :now, approved_by = 'user'
            WHERE id = :id
            """
        ),
        {"now": now, "id": action_uuid},
    )

    email_uuid = action.email_id
    if email_uuid:
        await db.execute(
            text("UPDATE emails SET status = 'Replied' WHERE id = :email_id"),
            {"email_id": email_uuid},
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
            "entity_type": "action",
            "entity_id": action.id,
            "action": "draft_approved",
            "performed_by": "user",
            "timestamp": datetime.now(timezone.utc),
            "diff": json.dumps({"email_id": str(email_uuid) if email_uuid else None}),
        },
    )
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

