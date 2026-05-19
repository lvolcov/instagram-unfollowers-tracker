"""Tracked-account CRUD.

Adding a tracked account is done via the LoginAccount's live Playwright session:
we look up the username through Instagram's web_profile_info endpoint and check
the friendship relationship in one go. If the LoginAccount does not follow the
target, the request is rejected with 422.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.instagram.browser_session import open_logged_in_page
from backend.app.models.login_account import LoginAccount
from backend.app.models.tracked_account import TrackedAccount
from backend.app.schemas.tracked_account import (
    TrackedAccountCreate,
    TrackedAccountRead,
)

router = APIRouter()


@router.get("", response_model=list[TrackedAccountRead])
async def list_tracked(db: AsyncSession = Depends(get_db)) -> list[TrackedAccount]:
    result = await db.execute(select(TrackedAccount).order_by(TrackedAccount.created_at))
    return list(result.scalars().all())


@router.get("/{tracked_id}", response_model=TrackedAccountRead)
async def get_tracked(tracked_id: int, db: AsyncSession = Depends(get_db)) -> TrackedAccount:
    tracked = await db.get(TrackedAccount, tracked_id)
    if not tracked:
        raise HTTPException(status_code=404, detail="Tracked account not found")
    return tracked


@router.post("", response_model=TrackedAccountRead)
async def add_tracked(
    payload: TrackedAccountCreate, db: AsyncSession = Depends(get_db)
) -> TrackedAccount:
    login = (await db.execute(select(LoginAccount))).scalar_one_or_none()
    if not login:
        raise HTTPException(status_code=400, detail="No login account configured")

    username = payload.username.lstrip("@").strip().lower()
    if not username:
        raise HTTPException(status_code=422, detail="Username is required")

    async with open_logged_in_page(login.session_path) as ig:
        info = await ig.user_info_by_username(username)
        if not info:
            raise HTTPException(status_code=404, detail=f"@{username} not found on Instagram")
        status = await ig.friendship_status(info["instagram_user_id"])

    if not status.following:
        raise HTTPException(
            status_code=422,
            detail=(
                f"@{login.username} does not follow @{username}. "
                "Follow this account from the logged-in profile, then try again."
            ),
        )

    tracked = TrackedAccount(
        login_account_id=login.id,
        instagram_user_id=info["instagram_user_id"],
        username=info["username"],
        display_name=info.get("full_name"),
        profile_pic_url=info.get("profile_pic_url"),
        is_private=bool(info.get("is_private", False)),
        follows_us=status.followed_by,
        we_follow=status.following,
    )
    db.add(tracked)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail=f"@{username} is already tracked")
    await db.refresh(tracked)
    return tracked


@router.delete("/{tracked_id}")
async def delete_tracked(tracked_id: int, db: AsyncSession = Depends(get_db)) -> dict:
    tracked = await db.get(TrackedAccount, tracked_id)
    if not tracked:
        raise HTTPException(status_code=404, detail="Tracked account not found")
    await db.delete(tracked)
    await db.commit()
    return {"deleted": True}
