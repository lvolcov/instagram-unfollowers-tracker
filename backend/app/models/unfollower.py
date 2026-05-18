"""Unfollower log — permanent record of detected unfollows."""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base


class Unfollower(Base):
    __tablename__ = "unfollowers"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    instagram_user_id: Mapped[str] = mapped_column(String, index=True)
    username: Mapped[str] = mapped_column(String)
    full_name: Mapped[str | None] = mapped_column(String, nullable=True)
    profile_pic_url: Mapped[str | None] = mapped_column(String, nullable=True)

    detected_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
    first_seen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    notified: Mapped[bool] = mapped_column(Boolean, default=False)
