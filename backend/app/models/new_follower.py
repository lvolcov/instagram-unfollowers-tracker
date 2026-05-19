"""New-follower log — permanent record of newly detected followers per tracked account."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base


class NewFollower(Base):
    __tablename__ = "new_followers"

    id: Mapped[int] = mapped_column(primary_key=True)
    tracked_account_id: Mapped[int] = mapped_column(
        ForeignKey("tracked_accounts.id", ondelete="CASCADE"), index=True
    )
    instagram_user_id: Mapped[str] = mapped_column(String, index=True)
    username: Mapped[str] = mapped_column(String)
    full_name: Mapped[str | None] = mapped_column(String, nullable=True)
    profile_pic_url: Mapped[str | None] = mapped_column(String, nullable=True)

    detected_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
