"""Home Assistant webhook delivery with retry/backoff."""
from __future__ import annotations

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from backend.app.core.config import settings


class WebhookService:
    @property
    def url(self) -> str:
        return f"{settings.HA_WEBHOOK_URL.rstrip('/')}/api/webhook/{settings.HA_WEBHOOK_ID}"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.HTTPError),
    )
    async def send(self, *, account: str, unfollowers: list[str]) -> dict:
        if not settings.HA_WEBHOOK_ENABLED:
            return {"sent": False, "reason": "disabled"}
        payload = {
            "account": account,
            "unfollowers": unfollowers,
            "count": len(unfollowers),
        }
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(self.url, json=payload)
            response.raise_for_status()
            return {
                "sent": True,
                "status_code": response.status_code,
                "response_ms": int(response.elapsed.total_seconds() * 1000),
            }

    async def send_test(self) -> dict:
        try:
            return await self.send(account="test_account", unfollowers=["test_user"])
        except Exception as e:  # noqa: BLE001
            return {"sent": False, "error": str(e), "url": self.url}


webhook_service = WebhookService()
