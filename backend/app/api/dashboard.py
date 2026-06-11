from fastapi import APIRouter, Depends
from sqlalchemy import text

from app.database import get_db

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats")
async def get_dashboard_stats(db=Depends(get_db)):
    stmt = text(
        """
        SELECT
            COUNT(*) FILTER (WHERE status IN ('Received', 'Processing')) AS pending,
            COUNT(*) FILTER (WHERE status = 'Replied') AS replied,
            COUNT(*) FILTER (WHERE status = 'Escalated') AS escalated,
            COUNT(*) FILTER (WHERE urgency = 'Critical') AS critical,
            COUNT(*) FILTER (WHERE category = 'Spam') AS spam_filtered,
            COUNT(*) AS total
        FROM emails
        """
    )
    result = await db.execute(stmt)
    row = result.fetchone()

    return {
        "pending": row.pending or 0,
        "replied": row.replied or 0,
        "escalated": row.escalated or 0,
        "critical": row.critical or 0,
        "spam_filtered": row.spam_filtered or 0,
        "total": row.total or 0,
    }

