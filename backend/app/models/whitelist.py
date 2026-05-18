"""Whitelist — accounts user marks as 'OK to not follow back'."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base


class WhitelistEntry(Base):
    __tablename__ = "whitelist"
    __table_args__ = (
        UniqueConstraint("account_id", "instagram_user_id", name="uq_whitelist_account_user"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    instagram_user_id: Mapped[str] = mapped_column(String, index=True)
    username: Mapped[str] = mapped_column(String)
    note: Mapped[str | None] = mapped_column(String, nullable=True)

    added_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
