"""Single LoginAccount endpoints — get / delete the viewer session."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.instagram.session_store import delete_session
from backend.app.models.login_account import LoginAccount
from backend.app.schemas.login_account import LoginAccountRead

router = APIRouter()


@router.get("", response_model=LoginAccountRead | None)
async def get_login_account(db: AsyncSession = Depends(get_db)) -> LoginAccount | None:
    result = await db.execute(select(LoginAccount).limit(1))
    return result.scalar_one_or_none()


@router.delete("")
async def delete_login_account(db: AsyncSession = Depends(get_db)) -> dict:
    """Log out: remove the LoginAccount row, encrypted session file, and all tracked data."""
    result = await db.execute(select(LoginAccount))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="No login account configured")
    if account.session_path:
        delete_session(account.session_path)
    # Cascades wipe tracked_accounts / snapshots / unfollowers / whitelist / schedules.
    await db.delete(account)
    await db.commit()
    return {"deleted": True}
