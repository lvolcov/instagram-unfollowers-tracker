"""CRUD endpoints for tracked Instagram accounts."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.models.account import Account
from backend.app.schemas.account import AccountRead

router = APIRouter()


@router.get("", response_model=list[AccountRead])
async def list_accounts(db: AsyncSession = Depends(get_db)) -> list[Account]:
    result = await db.execute(select(Account).order_by(Account.created_at))
    return list(result.scalars().all())


@router.get("/{account_id}", response_model=AccountRead)
async def get_account(account_id: int, db: AsyncSession = Depends(get_db)) -> Account:
    account = await db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


@router.delete("/{account_id}")
async def delete_account(account_id: int, db: AsyncSession = Depends(get_db)) -> dict:
    account = await db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    await db.delete(account)
    await db.commit()
    return {"deleted": True}


@router.post("/{account_id}/reauth")
async def reauth_account(account_id: int, db: AsyncSession = Depends(get_db)) -> dict:
    """Start a new login flow for an existing account whose session expired."""
    account = await db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    # TODO: implementation in Phase 1
    return {"status": "not_implemented"}
