"""Endpoints for followers / following / non-followers from the latest snapshot."""
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.models.snapshot import Snapshot, SnapshotUser
from backend.app.models.whitelist import WhitelistEntry

router = APIRouter()


async def _latest_snapshot(account_id: int, db: AsyncSession) -> int | None:
    result = await db.execute(
        select(Snapshot.id)
        .where(Snapshot.account_id == account_id, Snapshot.status == "completed")
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


@router.get("/{account_id}/non-followers")
async def list_non_followers(
    account_id: int,
    include_whitelisted: bool = False,
    search: str = "",
    page: int = 1,
    page_size: int = 50,
    db: AsyncSession = Depends(get_db),
) -> dict:
    snap_id = await _latest_snapshot(account_id, db)
    if snap_id is None:
        return {"users": [], "page": page, "page_size": page_size, "total": 0}

    stmt = select(SnapshotUser).where(
        SnapshotUser.snapshot_id == snap_id,
        SnapshotUser.relationship == "following",  # follows us but we don't follow back
    )
    if search:
        stmt = stmt.where(SnapshotUser.username.ilike(f"%{search}%"))

    if not include_whitelisted:
        wl_sub = select(WhitelistEntry.instagram_user_id).where(
            WhitelistEntry.account_id == account_id
        )
        stmt = stmt.where(SnapshotUser.instagram_user_id.not_in(wl_sub))

    total_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = total_result.scalar() or 0

    stmt = stmt.order_by(SnapshotUser.username).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    users = result.scalars().all()

    return {"users": [_user_dict(u) for u in users], "page": page, "page_size": page_size, "total": total}


@router.get("/{account_id}/followers")
async def list_followers(
    account_id: int,
    search: str = "",
    page: int = 1,
    page_size: int = 50,
    db: AsyncSession = Depends(get_db),
) -> dict:
    snap_id = await _latest_snapshot(account_id, db)
    if snap_id is None:
        return {"users": [], "page": page, "page_size": page_size, "total": 0}

    stmt = select(SnapshotUser).where(
        SnapshotUser.snapshot_id == snap_id,
        SnapshotUser.relationship.in_(["follower", "mutual"]),
    )
    if search:
        stmt = stmt.where(SnapshotUser.username.ilike(f"%{search}%"))

    total_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = total_result.scalar() or 0

    stmt = stmt.order_by(SnapshotUser.username).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    return {"users": [_user_dict(u) for u in result.scalars().all()], "page": page, "page_size": page_size, "total": total}


@router.get("/{account_id}/following")
async def list_following(
    account_id: int,
    search: str = "",
    page: int = 1,
    page_size: int = 50,
    db: AsyncSession = Depends(get_db),
) -> dict:
    snap_id = await _latest_snapshot(account_id, db)
    if snap_id is None:
        return {"users": [], "page": page, "page_size": page_size, "total": 0}

    stmt = select(SnapshotUser).where(
        SnapshotUser.snapshot_id == snap_id,
        SnapshotUser.relationship.in_(["following", "mutual"]),
    )
    if search:
        stmt = stmt.where(SnapshotUser.username.ilike(f"%{search}%"))

    total_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = total_result.scalar() or 0

    stmt = stmt.order_by(SnapshotUser.username).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    return {"users": [_user_dict(u) for u in result.scalars().all()], "page": page, "page_size": page_size, "total": total}
