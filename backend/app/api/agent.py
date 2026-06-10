from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.agent import run as run_agent

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/dry-run/{email_id}")
async def agent_dry_run(
    email_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    try:
        UUID(email_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "VALIDATION_ERROR",
                "message": "Invalid email ID format",
                "details": {"email_id": "Must be a valid UUID"},
            },
        )

    embedder = request.app.state.embedder
    if embedder is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "Embedding model not loaded",
                "details": {},
            },
        )

    # Intercept session commits to prevent persisting writes
    original_commit = db.commit

    async def dummy_commit():
        await db.flush()

    db.commit = dummy_commit

    try:
        result = await run_agent(email_id, db, embedder, dry_run=True)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "PROCESSING_ERROR",
                "message": f"Failed to execute agent dry-run: {exc}",
                "details": {"error": str(exc)},
            },
        )
    finally:
        db.commit = original_commit
        await db.rollback()

    return result
