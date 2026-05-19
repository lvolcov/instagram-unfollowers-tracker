"""Unfollower history per tracked account."""
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.models.unfollower import Unfollower
from backend.app.schemas.unfollower import UnfollowerRead

router = APIRouter()


@router.get("/{tracked_id}/unfollowers", response_model=list[UnfollowerRead])
async def list_unfollowers(
    tracked_id: int,
    since: datetime | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 50,
    db: AsyncSession = Depends(get_db),
) -> list[Unfollower]:
    stmt = (
        select(Unfollower)
        .where(Unfollower.tracked_account_id == tracked_id)
        .order_by(Unfollower.detected_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    if since:
        stmt = stmt.where(Unfollower.detected_at >= since)
    if search:
        stmt = stmt.where(Unfollower.username.ilike(f"%{search}%"))
    result = await db.execute(stmt)
    return list(result.scalars().all())
