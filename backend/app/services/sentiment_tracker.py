from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Email


async def get_sentiment_trend(sender_email: str, db: AsyncSession, days: int = 30) -> dict[str, Any]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(Email.timestamp, Email.sentiment_score)
        .where(
            Email.sender == sender_email,
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
        "sender": sender_email,
        "data_points": data_points,
        "moving_average": moving_average,
        "deteriorating": await detect_deterioration(sender_email, db),
    }


async def detect_deterioration(sender_email: str, db: AsyncSession) -> bool:
    result = await db.execute(
        select(Email.sentiment_score)
        .where(Email.sender == sender_email, Email.sentiment_score.is_not(None))
        .order_by(Email.timestamp.desc())
        .limit(3)
    )
    scores = [float(score) for score in result.scalars().all()]
    return len(scores) == 3 and all(score < -0.3 for score in scores)


async def compute_moving_average(sender_email: str, db: AsyncSession, window: int = 5) -> float | None:
    result = await db.execute(
        select(Email.sentiment_score)
        .where(Email.sender == sender_email, Email.sentiment_score.is_not(None))
        .order_by(Email.timestamp.desc())
        .limit(window)
    )
    scores = [float(score) for score in result.scalars().all()]
    return sum(scores) / len(scores) if scores else None
