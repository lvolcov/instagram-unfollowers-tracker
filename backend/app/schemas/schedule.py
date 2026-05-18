"""Pydantic schemas for Schedule API."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class ScheduleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: int
    mode: Literal["daily_at", "interval_hours", "manual_only"]
    daily_time: str | None
    interval_hours: int | None
    enabled: bool
    next_run_at: datetime | None


class ScheduleUpdate(BaseModel):
    mode: Literal["daily_at", "interval_hours", "manual_only"]
    daily_time: str | None = None
    interval_hours: int | None = None
    enabled: bool = True
