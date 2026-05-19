"""Snapshot ORM models — historical follower/following lists per tracked account."""
from datetime import datetime
from typing import Literal

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base

SnapshotStatus = Literal["running", "completed", "failed"]
Relationship = Literal["follower", "following", "mutual"]


class Snapshot(Base):
    __tablename__ = "snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    tracked_account_id: Mapped[int] = mapped_column(
        ForeignKey("tracked_accounts.id", ondelete="CASCADE"), index=True
    )
    taken_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
    followers_count: Mapped[int] = mapped_column(Integer, default=0)
    following_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String, default="running")
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)


class SnapshotUser(Base):
    __tablename__ = "snapshot_users"
    __table_args__ = (
        Index("ix_snapshot_users_snapshot_iguid", "snapshot_id", "instagram_user_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    snapshot_id: Mapped[int] = mapped_column(
        ForeignKey("snapshots.id", ondelete="CASCADE"), index=True
    )
    instagram_user_id: Mapped[str] = mapped_column(String, index=True)
    username: Mapped[str] = mapped_column(String)
    full_name: Mapped[str | None] = mapped_column(String, nullable=True)
    profile_pic_url: Mapped[str | None] = mapped_column(String, nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_private: Mapped[bool] = mapped_column(Boolean, default=False)
    relationship: Mapped[str] = mapped_column(String)  # follower / following / mutual
