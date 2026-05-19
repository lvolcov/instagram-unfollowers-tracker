"""Pydantic schemas for the LoginAccount."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LoginAccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    instagram_user_id: str
    username: str
    display_name: str | None
    profile_pic_url: str | None
    session_status: str
    created_at: datetime
    last_active_at: datetime | None
