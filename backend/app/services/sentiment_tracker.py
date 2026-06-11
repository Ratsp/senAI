from datetime import datetime, timedelta, timezone
from typing import Any
from sqlalchemy import text


async def get_sentiment_trend(sender_email: str, db, days: int = 30) -> dict[str, Any]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        text(
            """
            SELECT timestamp, sentiment_score FROM emails
            WHERE sender = :sender AND timestamp >= :cutoff AND sentiment_score IS NOT NULL
            ORDER BY timestamp ASC
            """
        ),
        {"sender": sender_email, "cutoff": cutoff},
    )
    rows = result.fetchall()
    data_points = [
        {"timestamp": row.timestamp.isoformat(), "score": float(row.sentiment_score)}
        for row in rows
        if row.sentiment_score is not None
    ]
    last_scores = [point["score"] for point in data_points[-5:]]
    moving_average = sum(last_scores) / len(last_scores) if last_scores else None
    return {
        "sender": sender_email,
        "data_points": data_points,
        "moving_average": moving_average,
        "deteriorating": await detect_deterioration(sender_email, db),
    }


from app.config import settings

async def detect_deterioration(sender_email: str, db) -> bool:
    limit = settings.sentiment_consecutive_count
    threshold = settings.sentiment_threshold
    result = await db.execute(
        text(
            f"""
            SELECT sentiment_score FROM emails
            WHERE sender = :sender AND sentiment_score IS NOT NULL
            ORDER BY timestamp DESC
            LIMIT {limit}
            """
        ),
        {"sender": sender_email},
    )
    scores = [float(row.sentiment_score) for row in result.fetchall() if row.sentiment_score is not None]
    return len(scores) == limit and all(score < threshold for score in scores)


async def compute_moving_average(sender_email: str, db, window: int = 5) -> float | None:
    result = await db.execute(
        text(
            """
            SELECT sentiment_score FROM emails
            WHERE sender = :sender AND sentiment_score IS NOT NULL
            ORDER BY timestamp DESC
            LIMIT :window
            """
        ),
        {"sender": sender_email, "window": window},
    )
    scores = [float(row.sentiment_score) for row in result.fetchall() if row.sentiment_score is not None]
    return sum(scores) / len(scores) if scores else None

