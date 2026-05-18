"""Outbound webhook helpers (kept for symmetry; main config under /settings)."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/info")
async def webhook_info() -> dict:
    """Return the resolved webhook URL the container will POST to."""
    from backend.app.core.config import settings

    return {
        "url": f"{settings.HA_WEBHOOK_URL.rstrip('/')}/api/webhook/{settings.HA_WEBHOOK_ID}",
        "enabled": settings.HA_WEBHOOK_ENABLED,
    }
