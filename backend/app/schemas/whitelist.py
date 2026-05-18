"""Pydantic schemas for Whitelist API."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class WhitelistRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: int
    instagram_user_id: str
    username: str
    note: str | None
    added_at: datetime


class WhitelistCreate(BaseModel):
    instagram_user_id: str
    username: str
    note: str | None = None
