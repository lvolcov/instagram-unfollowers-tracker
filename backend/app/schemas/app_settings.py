"""Pydantic schemas for runtime app settings (singleton)."""
from pydantic import BaseModel, ConfigDict


class AppSettingsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    health_webhook_url: str | None


class AppSettingsUpdate(BaseModel):
    health_webhook_url: str | None = None
