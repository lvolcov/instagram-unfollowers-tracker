"""AppSettings — singleton row holding values that must be user-editable
at runtime (no .env / restart required). Currently only the health webhook.
"""
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base


class AppSettings(Base):
    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    health_webhook_url: Mapped[str | None] = mapped_column(String, nullable=True)
