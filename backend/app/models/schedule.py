"""Schedule ORM model — many schedules per tracked account.

Each row is one scheduled scan; an account can have several (e.g. daily morning
+ a weekly recap). Webhook URL on the row overrides the global default.
"""
from datetime import datetime
from typing import Literal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base

ScheduleMode = Literal["daily_at", "weekly_on", "interval_hours"]


class Schedule(Base):
    __tablename__ = "schedules"

    id: Mapped[int] = mapped_column(primary_key=True)
    tracked_account_id: Mapped[int] = mapped_column(
        ForeignKey("tracked_accounts.id", ondelete="CASCADE"), index=True
    )

    name: Mapped[str] = mapped_column(String, default="")
    mode: Mapped[str] = mapped_column(String, default="daily_at")
    daily_time: Mapped[str | None] = mapped_column(String, nullable=True)  # "HH:MM"
    weekly_day: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 0=Mon..6=Sun
    interval_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Per-schedule webhook override. NULL → use HA defaults from .env.
    webhook_url: Mapped[str | None] = mapped_column(String, nullable=True)

    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_run_status: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=__import__("sqlalchemy").func.current_timestamp()
    )
