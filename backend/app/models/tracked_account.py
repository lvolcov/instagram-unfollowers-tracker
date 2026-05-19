"""TrackedAccount — an Instagram account whose followers/following we scan.

The login account (see login_account.py) must follow this account, otherwise
private profiles return no data and even public ones get rate-limited harder.
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base


class TrackedAccount(Base):
    __tablename__ = "tracked_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    login_account_id: Mapped[int] = mapped_column(
        ForeignKey("login_accounts.id", ondelete="CASCADE"), index=True
    )
    instagram_user_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    username: Mapped[str] = mapped_column(String, index=True)
    display_name: Mapped[str | None] = mapped_column(String, nullable=True)
    profile_pic_url: Mapped[str | None] = mapped_column(String, nullable=True)

    is_private: Mapped[bool] = mapped_column(Boolean, default=False)
    follows_us: Mapped[bool] = mapped_column(Boolean, default=False)  # tracked → login
    we_follow: Mapped[bool] = mapped_column(Boolean, default=False)  # login → tracked

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
    last_scan_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
