"""Pydantic schemas for NewFollower API."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NewFollowerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tracked_account_id: int
    instagram_user_id: str
    username: str
    full_name: str | None
    profile_pic_url: str | None
    detected_at: datetime
