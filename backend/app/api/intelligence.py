from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import text

from app.database import get_db

router = APIRouter(prefix="/intelligence", tags=["intelligence"])


@router.get("/reputation")
async def get_latest_reputation(db=Depends(get_db)):
    now = datetime.now(timezone.utc)
    res = await db.execute(
        text(
            """
            SELECT scraped_data FROM web_intelligence_cache
            WHERE expires_at > :now
            ORDER BY scraped_at DESC
            LIMIT 1
            """
        ),
        {"now": now},
    )
    row = res.fetchone()

    if row:
        return row.scraped_data

    return {"message": "No reputation data available"}

