"""Whitelist CRUD for a tracked account."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.models.whitelist import WhitelistEntry
from backend.app.schemas.whitelist import WhitelistCreate, WhitelistRead

router = APIRouter()


@router.get("/{tracked_id}/whitelist", response_model=list[WhitelistRead])
async def list_whitelist(
    tracked_id: int, db: AsyncSession = Depends(get_db)
) -> list[WhitelistEntry]:
    stmt = select(WhitelistEntry).where(WhitelistEntry.tracked_account_id == tracked_id)
    return list((await db.execute(stmt)).scalars().all())


@router.post("/{tracked_id}/whitelist", response_model=WhitelistRead)
async def add_to_whitelist(
    tracked_id: int,
    payload: WhitelistCreate,
    db: AsyncSession = Depends(get_db),
) -> WhitelistEntry:
    entry = WhitelistEntry(
        tracked_account_id=tracked_id,
        instagram_user_id=payload.instagram_user_id,
        username=payload.username,
        note=payload.note,
    )
    db.add(entry)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Already whitelisted")
    await db.refresh(entry)
    return entry


@router.delete("/{tracked_id}/whitelist/{entry_id}")
async def remove_from_whitelist(
    tracked_id: int, entry_id: int, db: AsyncSession = Depends(get_db)
) -> dict:
    entry = await db.get(WhitelistEntry, entry_id)
    if not entry or entry.tracked_account_id != tracked_id:
        raise HTTPException(status_code=404, detail="Whitelist entry not found")
    await db.delete(entry)
    await db.commit()
    return {"deleted": True}
