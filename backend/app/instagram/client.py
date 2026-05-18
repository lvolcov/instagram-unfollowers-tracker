"""Instagram GraphQL client.

Uses the same query hash and pagination strategy as the original
InstagramUnfollowers browser tool (David Arroyo, MIT licensed) but
runs server-side with cookies extracted from a Playwright session.

Endpoint:
  GET https://www.instagram.com/graphql/query/
    ?query_hash=3dec7e2c57367ef3da3d987d89f9dbc8
    &variables={"id":"<ds_user_id>","include_reel":"true","fetch_mutual":"false","first":"24","after":"<cursor>"}

Required cookies:
  - sessionid
  - ds_user_id
  - csrftoken
"""
from __future__ import annotations

import asyncio
import random
from collections.abc import AsyncIterator
from dataclasses import dataclass

import httpx

from backend.app.core.config import settings

QUERY_HASH = "3dec7e2c57367ef3da3d987d89f9dbc8"
GRAPHQL_URL = "https://www.instagram.com/graphql/query/"


@dataclass
class IGUser:
    id: str
    username: str
    full_name: str
    profile_pic_url: str
    is_private: bool
    is_verified: bool
    follows_viewer: bool
    followed_by_viewer: bool


class InstagramClient:
    def __init__(self, *, cookies: dict[str, str], user_agent: str | None = None) -> None:
        self._cookies = cookies
        self._user_agent = user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        )

    @property
    def ds_user_id(self) -> str:
        return self._cookies["ds_user_id"]

    async def iter_following(self, user_id: str | None = None) -> AsyncIterator[IGUser]:
        """Paginate over the user's `following` list.

        TODO (Phase 1):
        - Yield each user as IGUser
        - Implement realistic delays (settings.IG_TIME_BETWEEN_CYCLES_MS)
        - Backoff every 5 cycles (settings.IG_TIME_AFTER_FIVE_CYCLES_MS)
        - Handle 401/403 by raising SessionExpiredError
        """
        target_id = user_id or self.ds_user_id
        cursor: str | None = None
        cycles = 0

        async with httpx.AsyncClient(
            cookies=self._cookies,
            headers={"User-Agent": self._user_agent},
            timeout=15,
        ) as client:
            while True:
                variables = (
                    f'{{"id":"{target_id}","include_reel":"true",'
                    f'"fetch_mutual":"false","first":"24"'
                    + (f',"after":"{cursor}"' if cursor else "")
                    + "}"
                )
                response = await client.get(
                    GRAPHQL_URL,
                    params={"query_hash": QUERY_HASH, "variables": variables},
                )
                response.raise_for_status()
                data = response.json()["data"]["user"]["edge_follow"]

                for edge in data["edges"]:
                    node = edge["node"]
                    yield IGUser(
                        id=node["id"],
                        username=node["username"],
                        full_name=node.get("full_name", ""),
                        profile_pic_url=node.get("profile_pic_url", ""),
                        is_private=node.get("is_private", False),
                        is_verified=node.get("is_verified", False),
                        follows_viewer=node.get("follows_viewer", False),
                        followed_by_viewer=node.get("followed_by_viewer", False),
                    )

                if not data["page_info"]["has_next_page"]:
                    break
                cursor = data["page_info"]["end_cursor"]

                # Human-like delay
                base = settings.IG_TIME_BETWEEN_CYCLES_MS / 1000
                await asyncio.sleep(base + random.uniform(0.5, 2.0))
                cycles += 1
                if cycles % 5 == 0:
                    await asyncio.sleep(settings.IG_TIME_AFTER_FIVE_CYCLES_MS / 1000)

    async def iter_followers(self, user_id: str | None = None) -> AsyncIterator[IGUser]:
        """Paginate over the user's `followers` list.

        NOTE: Different query_hash needed than `iter_following`. The original
        tool only enumerates `edge_follow` (following). To detect unfollowers
        we actually compare against your `edge_followed_by` (followers) too.

        TODO (Phase 1): Find the correct query_hash for `edge_followed_by`
        from current IG web client traffic — these hashes change occasionally.
        """
        raise NotImplementedError("To be implemented in Phase 1")


class SessionExpiredError(Exception):
    """Raised when IG cookies are no longer valid (401/403 from GraphQL)."""
