"""Instagram client that runs all requests INSIDE the live Chromium tab.

Rationale: requests fired from `httpx` (server-side) carry the wrong TLS/JA3
fingerprint, miss the browser-set sec-ch-ua-* and sec-fetch-* hints, and pair
session cookies issued by Chrome with a non-Chrome client. Instagram's anti-
automation correlates these signals and flags the account ("we detected unusual
activity"). By driving requests through `page.evaluate()` on a real
instagram.com tab, every request is byte-for-byte indistinguishable from the
user scrolling the followers modal.

The endpoint we call (`/api/v1/friendships/{uid}/{followers|following}/`) is the
same one Instagram's current web client uses; the X-IG-App-ID header (936...)
is the value its own JS sets. From inside the tab the browser supplies the
matching User-Agent automatically, so the previous "useragent mismatch" 400
goes away.
"""
from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass

import structlog

from backend.app.core.config import settings

IG_APP_ID = "936619743392459"
PAGE_SIZE = 50

logger = structlog.get_logger(__name__)


@dataclass
class IGUser:
    id: str
    username: str
    full_name: str
    profile_pic_url: str
    is_private: bool
    is_verified: bool


@dataclass
class FriendshipStatus:
    """Result of /api/v1/friendships/show/{uid}/ — perspective of the logged-in viewer."""

    following: bool          # viewer follows the target
    followed_by: bool        # target follows the viewer
    is_private: bool


class SessionExpiredError(Exception):
    """Raised when IG returns login_required / a redirect to /accounts/login."""


class NotFollowingError(Exception):
    """Raised when we try to scan a tracked account we don't follow."""


_FETCH_JSON = """
async ({path}) => {
  try {
    const r = await fetch(path, {
      credentials: 'include',
      headers: {
        'X-IG-App-ID': '936619743392459',
        'X-Requested-With': 'XMLHttpRequest',
      },
    });
    const text = await r.text();
    let body = null;
    try { body = JSON.parse(text); } catch (e) { body = {_raw: text}; }
    return {ok: r.ok, status: r.status, body};
  } catch (e) {
    return {ok: false, status: 0, body: {_exception: String(e)}};
  }
}
"""


def _jitter_short() -> float:
    """Per-page jitter ~ bookmarklet-style: 500–2000 ms micro + 700–1300 ms base."""
    base = settings.IG_TIME_BETWEEN_CYCLES_MS / 1000  # 1s default
    return base * random.uniform(0.7, 1.3) + random.uniform(0.5, 2.0)


def _jitter_long() -> float:
    """Every N cycles, wait longer with ±5 s jitter."""
    base = settings.IG_TIME_AFTER_FIVE_CYCLES_MS / 1000  # 10s default
    return max(0.0, base + random.uniform(-5.0, 5.0))


class BrowserIGClient:
    """Driven by a live Playwright Page already navigated to instagram.com."""

    def __init__(self, page) -> None:
        self._page = page

    async def _fetch(self, path: str) -> dict:
        result = await self._page.evaluate(_FETCH_JSON, {"path": path})
        if not result["ok"]:
            body = result.get("body") or {}
            if result["status"] in (401, 403):
                raise SessionExpiredError(
                    f"Instagram session expired (HTTP {result['status']}) — please re-login"
                )
            if isinstance(body, dict) and body.get("message") == "login_required":
                raise SessionExpiredError("Instagram session expired — please re-login")
            raise RuntimeError(f"IG fetch failed: status={result['status']} body={str(body)[:200]}")
        return result["body"]

    async def friendship_status(self, target_user_id: str) -> FriendshipStatus:
        """Return our (the logged-in viewer's) relationship to target_user_id."""
        data = await self._fetch(f"/api/v1/friendships/show/{target_user_id}/")
        return FriendshipStatus(
            following=bool(data.get("following")),
            followed_by=bool(data.get("followed_by")),
            is_private=bool(data.get("is_private")),
        )

    async def user_info(self, user_id: str) -> dict:
        """Return the canonical user info dict for `user_id`, including
        `follower_count` and `following_count` straight from Instagram.
        """
        data = await self._fetch(f"/api/v1/users/{user_id}/info/")
        return (data or {}).get("user", {}) or {}

    async def collect_complete(
        self,
        kind: str,  # "followers" | "following"
        target_user_id: str,
        expected_count: int,
        *,
        max_attempts: int = 30,
        max_consecutive_no_progress: int = 5,
        on_progress=None,
    ) -> tuple[list["IGUser"], int, bool]:
        """Paginate `kind` until we've seen `expected_count` unique users,
        or we plateau (an attempt adds zero new users), or we hit max_attempts.

        Returns (users, attempts_used, is_complete).

        Why retries: Instagram's followers/following endpoints return a
        personalised, re-ranked feed. Pagination via `next_max_id` can
        terminate before the full list is delivered, with a different slice
        appearing on each call. Re-running and unioning the IDs converges
        toward the canonical list.
        """
        base = f"/api/v1/friendships/{target_user_id}/{kind}/"
        seen: dict[str, IGUser] = {}
        attempt = 0
        consecutive_no_progress = 0
        previous_seen = -1

        while attempt < max_attempts:
            attempt += 1
            logger.info(
                "ig.collect.attempt",
                kind=kind,
                attempt=attempt,
                expected=expected_count,
                seen_before=len(seen),
            )
            async for user in self._paginate(base):
                if user.id not in seen:
                    seen[user.id] = user
                if on_progress:
                    on_progress(len(seen), expected_count, attempt)
                if expected_count and len(seen) >= expected_count:
                    break

            logger.info(
                "ig.collect.attempt_done",
                kind=kind,
                attempt=attempt,
                seen_after=len(seen),
                expected=expected_count,
            )

            if expected_count and len(seen) >= expected_count:
                return list(seen.values()), attempt, True

            # Track consecutive attempts that added nothing new. We only bail
            # once we've had `max_consecutive_no_progress` in a row — Instagram's
            # re-ranking sometimes returns the same slice 2-3 times before
            # finally surfacing the missing tail.
            if len(seen) == previous_seen:
                consecutive_no_progress += 1
                logger.info(
                    "ig.collect.no_progress",
                    kind=kind,
                    attempt=attempt,
                    seen=len(seen),
                    consecutive=consecutive_no_progress,
                    limit=max_consecutive_no_progress,
                )
                if consecutive_no_progress >= max_consecutive_no_progress:
                    logger.info(
                        "ig.collect.plateau",
                        kind=kind,
                        attempt=attempt,
                        seen=len(seen),
                    )
                    break
            else:
                consecutive_no_progress = 0
            previous_seen = len(seen)

            # Cool-off between attempts so the re-ranking can shuffle.
            wait = _jitter_long() * 2
            logger.info("ig.collect.cooldown", kind=kind, seconds=int(wait))
            await asyncio.sleep(wait)

        # If expected_count is 0 (e.g. canonical count missing), treat as complete
        # when there's nothing more to fetch.
        is_complete = (expected_count > 0 and len(seen) >= expected_count) or expected_count == 0
        return list(seen.values()), attempt, is_complete

    async def user_info_by_username(self, username: str) -> dict | None:
        """Look up a user by handle — returns the `user` dict or None if 404."""
        try:
            data = await self._fetch(f"/api/v1/users/web_profile_info/?username={username}")
        except RuntimeError:
            return None
        user = (data or {}).get("data", {}).get("user")
        if not user:
            return None
        return {
            "instagram_user_id": str(user.get("id", "")),
            "username": user.get("username", ""),
            "full_name": user.get("full_name") or None,
            "profile_pic_url": user.get("profile_pic_url_hd") or user.get("profile_pic_url"),
            "is_private": bool(user.get("is_private", False)),
        }

    async def iter_followers(self, target_user_id: str):
        async for u in self._paginate(f"/api/v1/friendships/{target_user_id}/followers/"):
            yield u

    async def iter_following(self, target_user_id: str):
        async for u in self._paginate(f"/api/v1/friendships/{target_user_id}/following/"):
            yield u

    async def _paginate(self, base_path: str):
        cursor: str | None = None
        cycles = 0
        while True:
            sep = "&" if "?" in base_path else "?"
            path = f"{base_path}{sep}count={PAGE_SIZE}"
            if cursor:
                path += f"&max_id={cursor}"

            data = await self._fetch(path)
            users_in_page = data.get("users", []) or []
            if not users_in_page:
                logger.warning(
                    "ig.paginate.empty_page",
                    path=path,
                    response_keys=list(data.keys()) if isinstance(data, dict) else None,
                    status=data.get("status") if isinstance(data, dict) else None,
                    message=data.get("message") if isinstance(data, dict) else None,
                    big_list=data.get("big_list") if isinstance(data, dict) else None,
                    next_max_id=data.get("next_max_id") if isinstance(data, dict) else None,
                    raw_snippet=str(data)[:300],
                )

            for raw in users_in_page:
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
            await asyncio.sleep(_jitter_short())
            if cycles % 5 == 0:
                wait = _jitter_long()
                logger.info("ig.long_pause", seconds=int(wait), cycles=cycles)
                await asyncio.sleep(wait)
