"""Outbound webhook delivery (Home Assistant + health monitoring).

Two flavours:
- `send_unfollowers(...)` — fires after a scan, payload `{account, unfollowers, count}`.
- `send_health(...)` — fires when something is wrong (e.g. session expired),
  payload `{event, ...}`.

Each accepts an optional `url` override; if omitted, the function uses the
configured default (HA from .env for scan webhooks; AppSettings.health_webhook_url
for health events).
"""
from __future__ import annotations

import httpx
import structlog
from sqlalchemy import select
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from backend.app.core.config import settings
from backend.app.core.database import AsyncSessionLocal
from backend.app.models.app_settings import AppSettings

logger = structlog.get_logger(__name__)


def _default_ha_url() -> str:
    return f"{settings.HA_WEBHOOK_URL.rstrip('/')}/api/webhook/{settings.HA_WEBHOOK_ID}"


async def _health_url() -> str | None:
    async with AsyncSessionLocal() as db:
        row = (await db.execute(select(AppSettings).limit(1))).scalar_one_or_none()
        return row.health_webhook_url if row else None


class WebhookService:
    @property
    def default_url(self) -> str:
        return _default_ha_url()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.HTTPError),
    )
    async def _post(self, url: str, payload: dict) -> dict:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return {
                "sent": True,
                "status_code": response.status_code,
                "response_ms": int(response.elapsed.total_seconds() * 1000),
            }

    async def send_unfollowers(
        self,
        *,
        account: str,
        unfollowers: list[str],
        url: str | None = None,
    ) -> dict:
        if not settings.HA_WEBHOOK_ENABLED:
            return {"sent": False, "reason": "disabled"}
        target = url or self.default_url
        payload = {"account": account, "unfollowers": unfollowers, "count": len(unfollowers)}
        return await self._post(target, payload)

    async def send_health(self, *, event: str, **extra) -> dict:
        url = await _health_url()
        if not url:
            logger.info("webhook.health.skipped", reason="no_url_configured", event=event)
            return {"sent": False, "reason": "no_url"}
        payload = {"event": event, **extra}
        try:
            result = await self._post(url, payload)
            logger.info("webhook.health.sent", event=event, url=url)
            return result
        except Exception as exc:
            logger.warning("webhook.health.failed", event=event, error=str(exc))
            return {"sent": False, "error": str(exc)}

    async def send_test(self, *, url: str | None = None) -> dict:
        target = url or self.default_url
        try:
            return await self._post(
                target, {"account": "test_account", "unfollowers": ["test_user"], "count": 1}
            )
        except Exception as e:
            return {"sent": False, "error": str(e), "url": target}

    async def send_test_health(self) -> dict:
        url = await _health_url()
        if not url:
            return {"sent": False, "error": "Health webhook URL not configured"}
        try:
            return await self._post(url, {"event": "test", "message": "Health webhook test"})
        except Exception as e:
            return {"sent": False, "error": str(e), "url": url}


webhook_service = WebhookService()
