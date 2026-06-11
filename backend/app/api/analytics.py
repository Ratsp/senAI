from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy import text

from app.database import get_db
from app.services.sentiment_tracker import get_sentiment_trend

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/sentiment-trend")
async def get_sentiment_trend_endpoint(
    sender: str | None = Query(default=None, description="Sender email filter"),
    days: int = Query(default=30, ge=1, description="Number of days to check"),
    db=Depends(get_db),
):
    if sender:
        return await get_sentiment_trend(sender, db, days=days)

    # Global sentiment trend if no sender is provided
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        text(
            """
            SELECT timestamp, sentiment_score FROM emails
            WHERE timestamp >= :cutoff AND sentiment_score IS NOT NULL
            ORDER BY timestamp ASC
            """
        ),
        {"cutoff": cutoff},
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
        "sender": "global",
        "data_points": data_points,
        "moving_average": moving_average,
        "deteriorating": False,
    }


@router.get("/category-breakdown")
async def get_category_breakdown(
    start_date: datetime | None = Query(default=None, description="Start range datetime"),
    end_date: datetime | None = Query(default=None, description="End range datetime"),
    db=Depends(get_db),
):
    query = "SELECT category, COUNT(id) AS count FROM emails"
    where_clauses = []
    params = {}
    if start_date:
        where_clauses.append("timestamp >= :start_date")
        params["start_date"] = start_date
    if end_date:
        where_clauses.append("timestamp <= :end_date")
        params["end_date"] = end_date
    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)
    query += " GROUP BY category"

    result = await db.execute(text(query), params)
    rows = result.fetchall()
    breakdown = {row.category or "Unclassified": row.count for row in rows}
    total = sum(breakdown.values())

    return {"breakdown": breakdown, "total": total}


@router.get("/heatmap")
async def get_activity_heatmap(db=Depends(get_db)):
    result = await db.execute(
        text("""
            SELECT 
                EXTRACT(ISODOW FROM e.timestamp) AS day_of_week,
                EXTRACT(HOUR FROM e.timestamp) AS hour_of_day,
                AVG(EXTRACT(EPOCH FROM (a.executed_at - e.timestamp))) AS avg_response_time_seconds
            FROM emails e
            JOIN actions a ON a.email_id = e.id
            WHERE a.is_approved = TRUE AND a.executed_at IS NOT NULL
            GROUP BY day_of_week, hour_of_day
            ORDER BY day_of_week, hour_of_day
        """)
    )
    rows = result.fetchall()
    return [
        {
            "day_of_week": int(row.day_of_week),
            "hour_of_day": int(row.hour_of_day),
            "avg_response_time_seconds": float(row.avg_response_time_seconds) if row.avg_response_time_seconds is not None else 0.0
        }
        for row in rows
    ]


@router.get("/escalations")
async def get_escalation_analytics(db=Depends(get_db)):
    total_emails = await db.scalar(text("SELECT COUNT(id) FROM emails")) or 0
    total_escalated = await db.scalar(text("SELECT COUNT(id) FROM emails WHERE status = 'Escalated'")) or 0
    total_replied = await db.scalar(text("SELECT COUNT(id) FROM emails WHERE status = 'Replied'")) or 0
    avg_confidence = await db.scalar(text("SELECT AVG(confidence) FROM emails WHERE confidence IS NOT NULL")) or 0.0

    escalation_rate = total_escalated / total_emails if total_emails > 0 else 0.0
    auto_reply_rate = total_replied / total_emails if total_emails > 0 else 0.0

    cat_res = await db.execute(
        text("""
            SELECT category, COUNT(id) AS count FROM emails
            WHERE status = 'Escalated'
            GROUP BY category
        """)
    )
    cat_rows = cat_res.fetchall()
    escalations_by_category = {row.category or "Unclassified": row.count for row in cat_rows}

    return {
        "total_emails": total_emails,
        "total_escalated": total_escalated,
        "total_replied": total_replied,
        "escalation_rate": escalation_rate,
        "auto_reply_rate": auto_reply_rate,
        "average_confidence": float(avg_confidence),
        "escalations_by_category": escalations_by_category,
    }


@router.get("/at-risk-contacts")
async def get_at_risk_contacts(db=Depends(get_db)):
    result = await db.execute(
        text("""
            SELECT 
                c.id, c.email, c.name, c.company, c.status, c.account_value, c.churn_risk_score,
                (SELECT COUNT(*) FROM threads t WHERE t.sender_email = c.email AND t.status = 'Open') AS open_thread_count,
                (SELECT AVG(e.sentiment_score) FROM emails e WHERE e.sender = c.email AND e.sentiment_score IS NOT NULL) AS live_sentiment,
                (SELECT COUNT(*) FROM emails e JOIN threads t ON e.thread_id = t.id WHERE t.sender_email = c.email AND e.urgency = 'Critical' AND e.status IN ('Received', 'Processing', 'Escalated')) AS unresolved_critical_count
            FROM contacts c
            WHERE c.churn_risk_score > 0 OR c.status = 'At Risk'
            ORDER BY c.churn_risk_score DESC
            LIMIT 20
        """)
    )
    rows = result.fetchall()
    return [
        {
            "id": str(row.id),
            "email": row.email,
            "name": row.name,
            "company": row.company,
            "status": row.status,
            "account_value": float(row.account_value) if row.account_value is not None else 0.0,
            "churn_risk_score": float(row.churn_risk_score) if row.churn_risk_score is not None else 0.0,
            "open_thread_count": int(row.open_thread_count or 0),
            "live_sentiment": float(row.live_sentiment) if row.live_sentiment is not None else 0.0,
            "unresolved_critical_count": int(row.unresolved_critical_count or 0)
        }
        for row in rows
    ]

