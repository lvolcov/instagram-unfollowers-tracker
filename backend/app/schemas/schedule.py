"""Pydantic schemas for Schedule API."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


ScheduleMode = Literal["daily_at", "weekly_on", "interval_hours"]


class ScheduleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tracked_account_id: int
    name: str
    mode: ScheduleMode
    daily_time: str | None
    weekly_day: int | None
    interval_hours: int | None
    webhook_url: str | None
    enabled: bool
    next_run_at: datetime | None
    last_run_at: datetime | None
    last_run_status: str | None


class ScheduleCreate(BaseModel):
    tracked_account_id: int
    name: str = ""
    mode: ScheduleMode
    daily_time: str | None = None        # "HH:MM" — for daily_at / weekly_on
    weekly_day: int | None = None        # 0=Mon..6=Sun — for weekly_on
    interval_hours: int | None = None    # for interval_hours
    webhook_url: str | None = None       # override; None → .env default
    enabled: bool = True


class ScheduleUpdate(BaseModel):
    name: str | None = None
    mode: ScheduleMode | None = None
    daily_time: str | None = None
    weekly_day: int | None = None
    interval_hours: int | None = None
    webhook_url: str | None = None
    enabled: bool | None = None
