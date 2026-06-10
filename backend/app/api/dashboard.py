from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Email

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats")
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    stmt = select(
        func.count().filter(Email.status.in_(["Received", "Processing"])).label("pending"),
        func.count().filter(Email.status == "Replied").label("replied"),
        func.count().filter(Email.status == "Escalated").label("escalated"),
        func.count().filter(Email.urgency == "Critical").label("critical"),
        func.count().filter(Email.category == "Spam").label("spam_filtered"),
        func.count().label("total"),
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
