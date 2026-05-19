"""Followers / following / non-followers of a tracked account (latest snapshot)."""
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.models.snapshot import Snapshot, SnapshotUser
from backend.app.models.whitelist import WhitelistEntry

router = APIRouter()


async def _latest_snapshot(tracked_id: int, db: AsyncSession) -> int | None:
    result = await db.execute(
        select(Snapshot.id)
        .where(Snapshot.tracked_account_id == tracked_id, Snapshot.status == "completed")
        .order_by(Snapshot.id.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


def _user_dict(u: SnapshotUser) -> dict:
    return {
        "id": u.id,
        "instagram_user_id": u.instagram_user_id,
        "username": u.username,
        "full_name": u.full_name,
        "profile_pic_url": u.profile_pic_url,
        "is_verified": u.is_verified,
        "is_private": u.is_private,
        "relationship": u.relationship,
    }


@router.get("/{tracked_id}/non-followers")
async def list_non_followers(
    tracked_id: int,
    include_whitelisted: bool = False,
    search: str = "",
    page: int = 1,
    page_size: int = 50,
    db: AsyncSession = Depends(get_db),
) -> dict:
    snap_id = await _latest_snapshot(tracked_id, db)
    if snap_id is None:
        return {"users": [], "page": page, "page_size": page_size, "total": 0}

    stmt = select(SnapshotUser).where(
        SnapshotUser.snapshot_id == snap_id,
        SnapshotUser.relationship == "following",
    )
    if search:
        stmt = stmt.where(SnapshotUser.username.ilike(f"%{search}%"))
    if not include_whitelisted:
        wl_sub = select(WhitelistEntry.instagram_user_id).where(
            WhitelistEntry.tracked_account_id == tracked_id
        )
        stmt = stmt.where(SnapshotUser.instagram_user_id.not_in(wl_sub))

    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar() or 0
    stmt = stmt.order_by(SnapshotUser.username).offset((page - 1) * page_size).limit(page_size)
    users = (await db.execute(stmt)).scalars().all()
    return {
        "users": [_user_dict(u) for u in users],
        "page": page,
        "page_size": page_size,
        "total": total,
    }


@router.get("/{tracked_id}/followers")
async def list_followers(
    tracked_id: int,
    search: str = "",
    page: int = 1,
    page_size: int = 50,
    only_not_following_back: bool = False,
    db: AsyncSession = Depends(get_db),
) -> dict:
    snap_id = await _latest_snapshot(tracked_id, db)
    if snap_id is None:
        return {"users": [], "page": page, "page_size": page_size, "total": 0}

    relationships = ["follower"] if only_not_following_back else ["follower", "mutual"]
    stmt = select(SnapshotUser).where(
        SnapshotUser.snapshot_id == snap_id,
        SnapshotUser.relationship.in_(relationships),
    )
    if search:
        stmt = stmt.where(SnapshotUser.username.ilike(f"%{search}%"))
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar() or 0
    stmt = stmt.order_by(SnapshotUser.username).offset((page - 1) * page_size).limit(page_size)
    users = (await db.execute(stmt)).scalars().all()
    return {
        "users": [_user_dict(u) for u in users],
        "page": page,
        "page_size": page_size,
        "total": total,
    }


@router.get("/{tracked_id}/following")
async def list_following(
    tracked_id: int,
    search: str = "",
    page: int = 1,
    page_size: int = 50,
    db: AsyncSession = Depends(get_db),
) -> dict:
    snap_id = await _latest_snapshot(tracked_id, db)
    if snap_id is None:
        return {"users": [], "page": page, "page_size": page_size, "total": 0}

    stmt = select(SnapshotUser).where(
        SnapshotUser.snapshot_id == snap_id,
        SnapshotUser.relationship.in_(["following", "mutual"]),
    )
    if search:
        stmt = stmt.where(SnapshotUser.username.ilike(f"%{search}%"))
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar() or 0
    stmt = stmt.order_by(SnapshotUser.username).offset((page - 1) * page_size).limit(page_size)
    users = (await db.execute(stmt)).scalars().all()
    return {
        "users": [_user_dict(u) for u in users],
        "page": page,
        "page_size": page_size,
        "total": total,
    }
