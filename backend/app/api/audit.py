import json
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text

from app.database import get_db
from app.auth import verify_api_key

router = APIRouter(prefix="/audit", tags=["audit"], dependencies=[Depends(verify_api_key)])


@router.get("/{entity_type}/{entity_id}")
async def get_entity_audit_logs(
    entity_type: str,
    entity_id: str,
    db=Depends(get_db),
):
    try:
        entity_uuid = UUID(entity_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "VALIDATION_ERROR",
                "message": "Invalid entity ID format",
                "details": {"entity_id": "Must be a valid UUID"},
            },
        )

    result = await db.execute(
        text(
            """
            SELECT id, entity_type, entity_id, action, performed_by, timestamp, diff
            FROM audit_log
            WHERE entity_type = :entity_type AND entity_id = :entity_id
            ORDER BY timestamp DESC
            """
        ),
        {"entity_type": entity_type, "entity_id": entity_uuid},
    )
    logs = result.fetchall()

    return [
        {
            "id": str(log.id),
            "entity_type": log.entity_type,
            "entity_id": str(log.entity_id),
            "action": log.action,
            "performed_by": log.performed_by,
            "timestamp": log.timestamp.isoformat(),
            "diff": json.loads(log.diff) if isinstance(log.diff, str) else log.diff,
        }
        for log in logs
    ]

