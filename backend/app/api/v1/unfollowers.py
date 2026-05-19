"""Unfollower and new-follower history per tracked account."""
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.models.new_follower import NewFollower
from backend.app.models.unfollower import Unfollower
from backend.app.schemas.new_follower import NewFollowerRead
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


@router.get("/{tracked_id}/new-followers", response_model=list[NewFollowerRead])
async def list_new_followers(
    tracked_id: int,
    since: datetime | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 50,
    db: AsyncSession = Depends(get_db),
) -> list[NewFollower]:
    stmt = (
        select(NewFollower)
        .where(NewFollower.tracked_account_id == tracked_id)
        .order_by(NewFollower.detected_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    if since:
        stmt = stmt.where(NewFollower.detected_at >= since)
    if search:
        stmt = stmt.where(NewFollower.username.ilike(f"%{search}%"))
    result = await db.execute(stmt)
    return list(result.scalars().all())
