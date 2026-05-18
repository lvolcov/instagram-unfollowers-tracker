"""Whitelist CRUD + import/export endpoints."""
import json

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.models.whitelist import WhitelistEntry
from backend.app.schemas.whitelist import WhitelistCreate, WhitelistRead

router = APIRouter()


@router.get("/{account_id}/whitelist", response_model=list[WhitelistRead])
async def list_whitelist(
    account_id: int, db: AsyncSession = Depends(get_db)
) -> list[WhitelistEntry]:
    stmt = select(WhitelistEntry).where(WhitelistEntry.account_id == account_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("/{account_id}/whitelist", response_model=WhitelistRead)
async def add_to_whitelist(
    account_id: int,
    payload: WhitelistCreate,
    db: AsyncSession = Depends(get_db),
) -> WhitelistEntry:
    entry = WhitelistEntry(
        account_id=account_id,
        instagram_user_id=payload.instagram_user_id,
        username=payload.username,
        note=payload.note,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


@router.delete("/{account_id}/whitelist/{entry_id}")
async def remove_from_whitelist(
    account_id: int, entry_id: int, db: AsyncSession = Depends(get_db)
) -> dict:
    entry = await db.get(WhitelistEntry, entry_id)
    if not entry or entry.account_id != account_id:
        raise HTTPException(status_code=404, detail="Whitelist entry not found")
    await db.delete(entry)
    await db.commit()
    return {"deleted": True}


@router.post("/{account_id}/whitelist/import")
async def import_whitelist(
    account_id: int, file: UploadFile, db: AsyncSession = Depends(get_db)
) -> dict:
    """Bulk import from JSON file (compatible with original tool format)."""
    raw = await file.read()
    try:
        users = json.loads(raw)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")
    # TODO: validate + insert
    return {"imported": len(users)}


@router.get("/{account_id}/whitelist/export")
async def export_whitelist(
    account_id: int, db: AsyncSession = Depends(get_db)
) -> StreamingResponse:
    # TODO: stream JSON download
    return StreamingResponse(iter([b"[]"]), media_type="application/json")
