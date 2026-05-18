"""Global settings endpoints."""
from fastapi import APIRouter

from backend.app.core.config import settings
from backend.app.services.webhook_service import webhook_service

router = APIRouter()


@router.get("")
async def get_settings() -> dict:
    return {
        "timezone": settings.TIMEZONE,
        "snapshot_retention_days": settings.SNAPSHOT_RETENTION_DAYS,
        "ha_webhook_url": settings.HA_WEBHOOK_URL,
        "ha_webhook_id": settings.HA_WEBHOOK_ID,
        "ha_webhook_enabled": settings.HA_WEBHOOK_ENABLED,
        "ig_time_between_cycles_ms": settings.IG_TIME_BETWEEN_CYCLES_MS,
        "ig_time_after_five_cycles_ms": settings.IG_TIME_AFTER_FIVE_CYCLES_MS,
    }


@router.post("/webhook/test")
async def test_webhook() -> dict:
    """Fire a dummy payload at the configured HA webhook so the user can verify wiring."""
    result = await webhook_service.send_test()
    return result
