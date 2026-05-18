"""Instagram private REST API client.

Uses the same session cookies saved by Playwright login.
Endpoints mirror what the Instagram mobile app uses — more stable
than the old GraphQL hashes which rotate frequently.

Required cookies:  sessionid, ds_user_id, csrftoken
"""
from __future__ import annotations

import asyncio
import random
from collections.abc import AsyncIterator
from dataclasses import dataclass

import httpx

from backend.app.core.config import settings

BASE = "https://www.instagram.com"
IG_APP_ID = "936619743392459"

_DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


@dataclass
class IGUser:
    id: str
    username: str
    full_name: str
    profile_pic_url: str
    is_private: bool
    is_verified: bool


class SessionExpiredError(Exception):
    """Raised when IG returns 401 / 'login_required'."""


class InstagramClient:
    def __init__(self, *, cookies: dict[str, str], user_agent: str | None = None) -> None:
        self._cookies = cookies
        self._ua = user_agent or _DEFAULT_UA

    @property
    def ds_user_id(self) -> str:
        return self._cookies["ds_user_id"]

    def _make_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=BASE,
            cookies=self._cookies,
            headers={
                "User-Agent": self._ua,
                "X-IG-App-ID": IG_APP_ID,
                "X-Requested-With": "XMLHttpRequest",
                "X-CSRFToken": self._cookies.get("csrftoken", ""),
                "Referer": "https://www.instagram.com/",
            },
            timeout=20,
            follow_redirects=True,
        )

    async def iter_followers(self, user_id: str | None = None) -> AsyncIterator[IGUser]:
        """Yield every account that follows user_id (defaults to self)."""
        uid = user_id or self.ds_user_id
        async for user in self._paginate(f"/api/v1/friendships/{uid}/followers/"):
            yield user

    async def iter_following(self, user_id: str | None = None) -> AsyncIterator[IGUser]:
        """Yield every account that user_id follows (defaults to self)."""
        uid = user_id or self.ds_user_id
        async for user in self._paginate(f"/api/v1/friendships/{uid}/following/"):
            yield user

    async def _paginate(self, path: str) -> AsyncIterator[IGUser]:
        cursor: str | None = None
        cycles = 0

        async with self._make_client() as client:
            while True:
                params: dict = {"count": 100}
                if cursor:
                    params["max_id"] = cursor

                resp = await client.get(path, params=params)

                if resp.status_code == 401:
                    raise SessionExpiredError("Instagram session expired — please re-login")

                if resp.status_code == 429:
                    await asyncio.sleep(60)
                    resp = await client.get(path, params=params)

                resp.raise_for_status()
                data = resp.json()

                if data.get("status") == "fail" or "login_required" in str(data):
                    raise SessionExpiredError("Instagram session expired — please re-login")

                for raw in data.get("users", []):
                    yield IGUser(
                        id=str(raw.get("pk") or raw.get("id", "")),
                        username=raw.get("username", ""),
                        full_name=raw.get("full_name", "") or "",
                        profile_pic_url=raw.get("profile_pic_url", "") or "",
                        is_private=bool(raw.get("is_private", False)),
                        is_verified=bool(raw.get("is_verified", False)),
                    )

                cursor = data.get("next_max_id")
                if not cursor:
                    break

                cycles += 1
                delay = settings.IG_TIME_BETWEEN_CYCLES_MS / 1000
                await asyncio.sleep(delay + random.uniform(0.3, 1.5))
                if cycles % 5 == 0:
                    await asyncio.sleep(settings.IG_TIME_AFTER_FIVE_CYCLES_MS / 1000)
