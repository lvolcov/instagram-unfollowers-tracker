"""Schedule ORM model — per-account scan scheduling."""
from datetime import datetime
from typing import Literal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base

ScheduleMode = Literal["daily_at", "interval_hours", "manual_only"]


class Schedule(Base):
    __tablename__ = "schedules"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), unique=True, index=True)

    mode: Mapped[str] = mapped_column(String, default="manual_only")
    daily_time: Mapped[str | None] = mapped_column(String, nullable=True)  # "HH:MM"
    interval_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)

    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
