from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import WebIntelligenceCache

router = APIRouter(prefix="/intelligence", tags=["intelligence"])


@router.get("/reputation")
async def get_latest_reputation(db: AsyncSession = Depends(get_db)):
    now = datetime.now(timezone.utc)
    cached = await db.scalar(
        select(WebIntelligenceCache)
        .where(WebIntelligenceCache.expires_at > now)
        .order_by(WebIntelligenceCache.scraped_at.desc())
        .limit(1)
    )

    if cached:
        return cached.scraped_data

    return {"message": "No reputation data available"}
