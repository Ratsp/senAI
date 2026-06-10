from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Email
from app.services.sentiment_tracker import get_sentiment_trend

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/sentiment-trend")
async def get_sentiment_trend_endpoint(
    sender: str | None = Query(default=None, description="Sender email filter"),
    days: int = Query(default=30, ge=1, description="Number of days to check"),
    db: AsyncSession = Depends(get_db),
):
    if sender:
        return await get_sentiment_trend(sender, db, days=days)

    # Global sentiment trend if no sender is provided
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(Email.timestamp, Email.sentiment_score)
        .where(
            Email.timestamp >= cutoff,
            Email.sentiment_score.is_not(None),
        )
        .order_by(Email.timestamp.asc())
    )
    data_points = [
        {"timestamp": timestamp.isoformat(), "score": float(score)}
        for timestamp, score in result.all()
        if score is not None
    ]
    last_scores = [point["score"] for point in data_points[-5:]]
    moving_average = sum(last_scores) / len(last_scores) if last_scores else None

    return {
        "sender": "global",
        "data_points": data_points,
        "moving_average": moving_average,
        "deteriorating": False,
    }


@router.get("/category-breakdown")
async def get_category_breakdown(
    start_date: datetime | None = Query(default=None, description="Start range datetime"),
    end_date: datetime | None = Query(default=None, description="End range datetime"),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Email.category, func.count(Email.id)).group_by(Email.category)
    if start_date:
        stmt = stmt.where(Email.timestamp >= start_date)
    if end_date:
        stmt = stmt.where(Email.timestamp <= end_date)

    result = await db.execute(stmt)
    breakdown = {category or "Unclassified": count for category, count in result.all()}
    total = sum(breakdown.values())

    return {"breakdown": breakdown, "total": total}
