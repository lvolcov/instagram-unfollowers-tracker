"""Unit tests for WebhookService URL construction and disabled-path behaviour."""
import asyncio
import sys
import os
import threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from cryptography.fernet import Fernet
from unittest.mock import patch

os.environ.setdefault("SECRET_KEY", Fernet.generate_key().decode())
os.environ.setdefault("HA_WEBHOOK_URL", "http://192.168.1.107:8123")
os.environ.setdefault("HA_WEBHOOK_ID", "instagram_unfollowers")

from backend.app.services.webhook_service import WebhookService


def _sync(coro):
    """Run a coroutine in a fresh thread+event-loop, avoiding conflicts with pytest-playwright."""
    result: list = [None]
    exc: list = [None]

    def run() -> None:
        try:
            result[0] = asyncio.run(coro)
        except Exception as e:  # noqa: BLE001
            exc[0] = e

    t = threading.Thread(target=run, daemon=True)
    t.start()
    t.join()
    if exc[0] is not None:
        raise exc[0]
    return result[0]


def test_webhook_url_constructed_correctly():
    """URL must follow the pattern {base}/api/webhook/{id} regardless of env values."""
    with patch("backend.app.services.webhook_service.settings") as mock_settings:
        mock_settings.HA_WEBHOOK_URL = "http://192.168.1.107:8123"
        mock_settings.HA_WEBHOOK_ID = "instagram_unfollowers"
        mock_settings.HA_WEBHOOK_ENABLED = True
        svc = WebhookService()
        assert svc.url == "http://192.168.1.107:8123/api/webhook/instagram_unfollowers"


def test_webhook_url_strips_trailing_slash():
    """Trailing slash on base URL must not produce double-slash."""
    with patch("backend.app.services.webhook_service.settings") as mock_settings:
        mock_settings.HA_WEBHOOK_URL = "http://192.168.1.107:8123/"
        mock_settings.HA_WEBHOOK_ID = "my_webhook"
        mock_settings.HA_WEBHOOK_ENABLED = True
        svc = WebhookService()
        assert "//" not in svc.url.replace("http://", "").replace("https://", "")


def test_send_returns_disabled_when_webhook_disabled():
    async def _coro():
        with patch("backend.app.services.webhook_service.settings") as mock_settings:
            mock_settings.HA_WEBHOOK_URL = "http://localhost:8123"
            mock_settings.HA_WEBHOOK_ID = "test"
            mock_settings.HA_WEBHOOK_ENABLED = False
            svc = WebhookService()
            return await svc.send(account="testuser", unfollowers=["someone"])

    result = _sync(_coro())
    assert result == {"sent": False, "reason": "disabled"}


def test_send_test_returns_error_dict_on_connection_failure():
    async def _coro():
        with patch("backend.app.services.webhook_service.settings") as mock_settings:
            mock_settings.HA_WEBHOOK_URL = "http://localhost:1"
            mock_settings.HA_WEBHOOK_ID = "nope"
            mock_settings.HA_WEBHOOK_ENABLED = True
            svc = WebhookService()
            return await svc.send_test()

    result = _sync(_coro())
    assert result["sent"] is False
    assert "error" in result
