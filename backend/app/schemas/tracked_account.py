"""Pydantic schemas for TrackedAccount."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TrackedAccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    instagram_user_id: str
    username: str
    display_name: str | None
    profile_pic_url: str | None
    is_private: bool
    follows_us: bool
    we_follow: bool
    created_at: datetime
    last_scan_at: datetime | None


class TrackedAccountCreate(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)


class TrackedAccountStats(TrackedAccountRead):
    followers_count: int = 0
    following_count: int = 0
    non_followers_count: int = 0
    whitelisted_count: int = 0
    total_unfollowers_logged: int = 0
