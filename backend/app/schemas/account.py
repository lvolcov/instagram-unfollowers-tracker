"""Pydantic schemas for Account API."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    instagram_user_id: str
    username: str
    display_name: str | None
    profile_pic_url: str | None
    session_status: str
    created_at: datetime
    last_scan_at: datetime | None


class AccountStats(AccountRead):
    followers_count: int = 0
    following_count: int = 0
    non_followers_count: int = 0
    whitelisted_count: int = 0
    total_unfollowers_logged: int = 0
