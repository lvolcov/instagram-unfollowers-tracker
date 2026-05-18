"""Account ORM model — tracked Instagram accounts."""
from datetime import datetime
from typing import Literal

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base

SessionStatus = Literal["active", "needs_relogin", "expired", "scanning"]


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    instagram_user_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    username: Mapped[str] = mapped_column(String, index=True)
    display_name: Mapped[str | None] = mapped_column(String, nullable=True)
    profile_pic_url: Mapped[str | None] = mapped_column(String, nullable=True)

    # Encrypted Playwright storage state filename (relative to SESSIONS_DIR)
    session_path: Mapped[str] = mapped_column(String)
    session_status: Mapped[str] = mapped_column(String, default="active")

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
    last_scan_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
