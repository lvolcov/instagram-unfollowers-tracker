"""Runtime app settings (singleton) — currently just the health webhook URL."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.models.app_settings import AppSettings
from backend.app.schemas.app_settings import AppSettingsRead, AppSettingsUpdate
from backend.app.services.webhook_service import webhook_service

router = APIRouter()


async def _get_or_create(db: AsyncSession) -> AppSettings:
    row = (await db.execute(select(AppSettings).limit(1))).scalar_one_or_none()
    if row is None:
        row = AppSettings(id=1, health_webhook_url=None)
        db.add(row)
        await db.commit()
        await db.refresh(row)
    return row


@router.get("", response_model=AppSettingsRead)
async def get_app_settings(db: AsyncSession = Depends(get_db)) -> AppSettings:
    return await _get_or_create(db)


@router.put("", response_model=AppSettingsRead)
async def update_app_settings(
    payload: AppSettingsUpdate, db: AsyncSession = Depends(get_db)
) -> AppSettings:
    row = await _get_or_create(db)
    if payload.health_webhook_url is not None:
        # Empty string clears the URL; trim whitespace for safety.
        row.health_webhook_url = payload.health_webhook_url.strip() or None
    await db.commit()
    await db.refresh(row)
    return row


@router.post("/health-webhook/test")
async def test_health_webhook() -> dict:
    return await webhook_service.send_test_health()
