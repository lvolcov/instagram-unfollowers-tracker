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
# Page size for the GraphQL queries; the original bookmarklet uses 24.
GRAPHQL_PAGE_SIZE = 24

# GraphQL query hashes (legacy but still operational on instagram.com web).
# These are the same hashes the original InstagramUnfollowers bookmarklet uses
# (utils.ts in davidarroyo1234/InstagramUnfollowers). Each takes the same
# `{id, first, after?}` variables shape and returns `data.user.edge_follow` /
# `edge_followed_by` with `count`, `page_info{has_next_page, end_cursor}` and
# `edges[].node` containing id, username, full_name, profile_pic_url,
# is_private, is_verified, follows_viewer.
GRAPHQL_HASH_FOLLOWING = "3dec7e2c57367ef3da3d987d89f9dbc8"   # edge_follow
GRAPHQL_HASH_FOLLOWERS = "c76146de99bb02f6415203be841dd25a"   # edge_followed_by

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

    async def collect_via_graphql(
        self,
        target_user_id: str,
        kind: str,  # "followers" | "following"
        expected_count: int,
        *,
        max_attempts: int = 30,
        max_consecutive_no_progress: int = 5,
        on_progress=None,
    ) -> tuple[list[IGUser], bool]:
        """Paginate followers/following via the legacy GraphQL endpoint.

        This is what the original InstagramUnfollowers bookmarklet uses; the
        URL is `instagram.com/graphql/query/?query_hash=<HASH>&variables=...`
        with `id` = the target user id. Each response is JSON, no HTML SPA
        fallback — `fetch()` from inside the tab works identically to the
        bookmarklet.

        Returns (users, is_complete). De-dupes across pagination *and* across
        retry attempts (re-running the pagination from cursor=None surfaces
        previously-missed users because IG's edge order is personalised).
        """
        query_hash = (
            GRAPHQL_HASH_FOLLOWERS if kind == "followers" else GRAPHQL_HASH_FOLLOWING
        )
        edge_key = "edge_followed_by" if kind == "followers" else "edge_follow"

        seen: dict[str, IGUser] = {}
        attempt = 0
        consecutive_no_progress = 0
        previous_seen = -1

        while attempt < max_attempts:
            attempt += 1
            logger.info(
                "ig.gql.attempt",
                kind=kind,
                attempt=attempt,
                seen_before=len(seen),
                expected=expected_count,
            )
            cursor: str | None = None
            page_n = 0
            while True:
                vars_obj = {
                    "id": target_user_id,
                    "include_reel": "true",
                    "fetch_mutual": "false",
                    "first": str(GRAPHQL_PAGE_SIZE),
                }
                if cursor:
                    vars_obj["after"] = cursor
                # Mirror the bookmarklet's URL exactly: variables as a raw JSON
                # string in the query, no URL-encoding gymnastics inside JS.
                page_n += 1
                data = await self._page.evaluate(
                    """async ({hash, vars}) => {
                        try {
                            const url = 'https://www.instagram.com/graphql/query/'
                                + '?query_hash=' + hash
                                + '&variables=' + encodeURIComponent(JSON.stringify(vars));
                            const r = await fetch(url, {credentials: 'include'});
                            const text = await r.text();
                            let body = null;
                            try { body = JSON.parse(text); } catch (e) { body = {_raw: text.slice(0, 300)}; }
                            return {ok: r.ok, status: r.status, body};
                        } catch (e) {
                            return {ok: false, status: 0, body: {_exception: String(e)}};
                        }
                    }""",
                    {"hash": query_hash, "vars": vars_obj},
                )
                if not data["ok"]:
                    body = data.get("body") or {}
                    if data["status"] in (401, 403):
                        raise SessionExpiredError(
                            f"Instagram session expired (HTTP {data['status']})"
                        )
                    logger.warning(
                        "ig.gql.bad_response",
                        kind=kind,
                        status=data["status"],
                        body_preview=str(body)[:200],
                    )
                    break

                edge = (
                    ((data.get("body") or {}).get("data") or {}).get("user") or {}
                ).get(edge_key) or {}
                edges = edge.get("edges") or []
                if not edges and page_n == 1:
                    logger.warning(
                        "ig.gql.empty_first_page",
                        kind=kind,
                        body_preview=str(data.get("body"))[:300],
                    )
                for raw_edge in edges:
                    node = raw_edge.get("node") or {}
                    uid = str(node.get("id") or node.get("pk") or "")
                    if uid and uid not in seen:
                        seen[uid] = IGUser(
                            id=uid,
                            username=node.get("username", ""),
                            full_name=node.get("full_name", "") or "",
                            profile_pic_url=node.get("profile_pic_url", "") or "",
                            is_private=bool(node.get("is_private", False)),
                            is_verified=bool(node.get("is_verified", False)),
                        )
                if on_progress:
                    on_progress(len(seen), expected_count, attempt)

                page_info = edge.get("page_info") or {}
                if not page_info.get("has_next_page"):
                    break
                cursor = page_info.get("end_cursor")
                if not cursor:
                    break

                # Bookmarklet-style jitter between pages.
                await asyncio.sleep(_jitter_short())
                if page_n % 6 == 0:
                    pause = _jitter_long()
                    logger.info("ig.gql.long_pause", kind=kind, seconds=int(pause))
                    await asyncio.sleep(pause)

            logger.info(
                "ig.gql.attempt_done",
                kind=kind,
                attempt=attempt,
                seen_after=len(seen),
                expected=expected_count,
            )

            if expected_count and len(seen) >= expected_count:
                return list(seen.values()), True

            if len(seen) == previous_seen:
                consecutive_no_progress += 1
                if consecutive_no_progress >= max_consecutive_no_progress:
                    logger.info(
                        "ig.gql.plateau",
                        kind=kind,
                        attempt=attempt,
                        seen=len(seen),
                    )
                    break
            else:
                consecutive_no_progress = 0
            previous_seen = len(seen)

            # Cool-off between attempts so ranking shifts.
            wait = _jitter_long() * 2
            logger.info("ig.gql.cooldown", kind=kind, seconds=int(wait))
            await asyncio.sleep(wait)

        is_complete = expected_count > 0 and len(seen) >= expected_count
        return list(seen.values()), is_complete

    async def collect_via_modal(
        self,
        username: str,
        target_user_id: str,
        kind: str,  # "followers" | "following"
        expected_count: int,
        *,
        max_stale_scrolls: int = 15,
        max_total_scrolls: int = 800,
        on_progress=None,
    ) -> tuple[list[IGUser], bool]:
        """Open the followers/following modal as a real user would, then
        intercept the responses Instagram's own JS issues as we scroll.

        Why: spoofing `fetch('/api/v1/friendships/{uid}/followers/')` from
        `page.evaluate` no longer works — Instagram's gateway returns the SPA
        HTML shell unless the request was issued by IG's own JS (which carries
        a session-bound X-IG-WWW-Claim, X-ASBD-ID and other headers we can't
        easily forge). By driving the actual modal UI we let IG produce the
        request and we just listen for the response on the wire.
        """
        page = self._page
        captured: dict[str, IGUser] = {}
        endpoint_fragment = f"/api/v1/friendships/{target_user_id}/{kind}/"

        async def _on_response(resp) -> None:
            if endpoint_fragment not in resp.url:
                return
            if resp.status != 200:
                logger.warning(
                    "ig.modal.bad_response",
                    kind=kind,
                    url=resp.url,
                    status=resp.status,
                )
                return
            try:
                data = await resp.json()
            except Exception as exc:
                logger.warning("ig.modal.parse_error", error=str(exc))
                return
            new = 0
            for raw in data.get("users", []) or []:
                uid = str(raw.get("pk") or raw.get("id", ""))
                if uid and uid not in captured:
                    captured[uid] = IGUser(
                        id=uid,
                        username=raw.get("username", ""),
                        full_name=raw.get("full_name", "") or "",
                        profile_pic_url=raw.get("profile_pic_url", "") or "",
                        is_private=bool(raw.get("is_private", False)),
                        is_verified=bool(raw.get("is_verified", False)),
                    )
                    new += 1
            if new and on_progress:
                on_progress(len(captured), expected_count, 1)
            logger.info(
                "ig.modal.response",
                kind=kind,
                new=new,
                total=len(captured),
                expected=expected_count,
            )

        page.on("response", _on_response)
        try:
            logger.info("ig.modal.opening", username=username, kind=kind)
            # Direct URL to the modal — IG renders the profile + opens it.
            await page.goto(
                f"https://www.instagram.com/{username}/{kind}/",
                wait_until="domcontentloaded",
            )
            # Give the dialog time to mount and the first page to land.
            await asyncio.sleep(3)

            try:
                await page.wait_for_selector('div[role="dialog"]', timeout=10_000)
            except Exception:
                logger.warning("ig.modal.dialog_not_found", kind=kind)
                return list(captured.values()), False

            # Scroll the inner scroll container repeatedly. The exact DOM class
            # names rotate, so do it in JS by finding the element with
            # overflow-y: auto inside the dialog.
            scroll_js = """
            () => {
              const dlg = document.querySelector('div[role="dialog"]');
              if (!dlg) return false;
              const cand = Array.from(dlg.querySelectorAll('*')).find(el => {
                const s = getComputedStyle(el);
                return (s.overflowY === 'auto' || s.overflowY === 'scroll')
                  && el.scrollHeight > el.clientHeight;
              });
              if (!cand) return false;
              cand.scrollTo({top: cand.scrollHeight, behavior: 'auto'});
              return true;
            }
            """

            last_count = -1
            stale = 0
            for scroll_n in range(max_total_scrolls):
                if expected_count and len(captured) >= expected_count:
                    logger.info(
                        "ig.modal.reached_expected",
                        kind=kind,
                        count=len(captured),
                    )
                    break

                ok = await page.evaluate(scroll_js)
                if not ok:
                    # Dialog vanished or scroll container disappeared.
                    logger.warning(
                        "ig.modal.scroll_failed",
                        kind=kind,
                        scroll_n=scroll_n,
                        captured=len(captured),
                    )
                    break

                # Jitter between scrolls so IG sees a human cadence.
                await asyncio.sleep(random.uniform(0.8, 1.8))

                if len(captured) == last_count:
                    stale += 1
                    if stale >= max_stale_scrolls:
                        logger.info(
                            "ig.modal.plateau",
                            kind=kind,
                            scrolls=scroll_n + 1,
                            captured=len(captured),
                            expected=expected_count,
                        )
                        break
                else:
                    stale = 0
                    last_count = len(captured)

                # Bigger pause every 10 scrolls.
                if (scroll_n + 1) % 10 == 0:
                    pause = random.uniform(3.0, 6.0)
                    logger.info("ig.modal.long_pause", kind=kind, seconds=int(pause))
                    await asyncio.sleep(pause)
        finally:
            try:
                page.remove_listener("response", _on_response)
            except Exception:
                pass

        is_complete = expected_count > 0 and len(captured) >= expected_count
        logger.info(
            "ig.modal.done",
            kind=kind,
            captured=len(captured),
            expected=expected_count,
            complete=is_complete,
        )
        return list(captured.values()), is_complete

    async def go_to_profile(self, username: str) -> None:
        """Navigate the tab to https://www.instagram.com/{username}/.

        Mandatory before calling iter_followers / iter_following — Instagram's
        `/api/v1/friendships/{uid}/followers/` returns the HTML SPA shell
        instead of JSON unless the Referer header is a profile page URL.
        """
        url = f"https://www.instagram.com/{username}/"
        logger.info("ig.navigate_profile", username=username)
        await self._page.goto(url, wait_until="domcontentloaded")
        # Settle so IG's JS bootstraps the X-IG-WWW-Claim & friends.
        await asyncio.sleep(2)

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
        # `search_surface=follow_list_page` is the magic parameter Instagram's
        # own modal passes; without it the gateway returns the SPA HTML shell
        # for /followers/ instead of JSON. /following/ is more lenient and
        # works either way, but we send it for both for consistency.
        extra = "search_surface=follow_list_page"
        while True:
            sep = "&" if "?" in base_path else "?"
            path = f"{base_path}{sep}count={PAGE_SIZE}&{extra}"
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
