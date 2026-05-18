"""Endpoints for viewing followers / non-followers / following."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db

router = APIRouter()


@router.get("/{account_id}/followers")
async def list_followers(
    account_id: int,
    search: str | None = None,
    page: int = 1,
    page_size: int = 50,
    db: AsyncSession = Depends(get_db),
) -> dict:
    # TODO: query latest snapshot's followers
    return {"users": [], "page": page, "page_size": page_size, "total": 0}


@router.get("/{account_id}/non-followers")
async def list_non_followers(
    account_id: int,
    include_whitelisted: bool = False,
    search: str | None = None,
    page: int = 1,
    page_size: int = 50,
    db: AsyncSession = Depends(get_db),
) -> dict:
    # TODO: diff following \ followers, optionally filter whitelist
    return {
        "users": [],
        "page": page,
        "page_size": page_size,
        "total": 0,
        "include_whitelisted": include_whitelisted,
    }


@router.get("/{account_id}/following")
async def list_following(
    account_id: int,
    search: str | None = None,
    page: int = 1,
    page_size: int = 50,
    db: AsyncSession = Depends(get_db),
) -> dict:
    # TODO: query latest snapshot's following
    return {"users": [], "page": page, "page_size": page_size, "total": 0}
