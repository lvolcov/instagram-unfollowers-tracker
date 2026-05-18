"""Manages in-flight Instagram login sessions backed by Playwright + noVNC.

Each session spawns a Chromium window on the container's Xvfb display (:99).
The browser is visible to the user through noVNC → websockify → x11vnc.
Once the URL leaves the login flow, the storage state is encrypted and saved
and the account row is written to the database.
"""
from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Literal
from urllib.parse import urlparse

import structlog
from sqlalchemy import select

from backend.app.core.database import AsyncSessionLocal
from backend.app.instagram.session_store import save_session
from backend.app.models.account import Account

logger = structlog.get_logger(__name__)

LoginStatus = Literal["waiting", "logged_in", "failed", "expired", "cancelled"]

INSTAGRAM_LOGIN_URL = "https://www.instagram.com/accounts/login/"
INSTAGRAM_USER_API = "https://www.instagram.com/api/v1/accounts/current_user/?edit=true"

# Paths that mean the user has NOT yet completed the login flow
_LOGIN_FLOW_PATHS = (
    "/accounts/login",
    "/challenge",
    "/checkpoint",
    "/accounts/suspended",
)

_LOGIN_TIMEOUT_S = 600  # 10 minutes


@dataclass
class LoginSession:
    id: str
    status: LoginStatus = "waiting"
    account_summary: dict | None = None
    error: str | None = None
    _task: asyncio.Task | None = field(default=None, repr=False)
    _browser: object | None = field(default=None, repr=False)


class LoginSessionManager:
    def __init__(self) -> None:
        self._sessions: dict[str, LoginSession] = {}

    async def start(self) -> LoginSession:
        session = LoginSession(id=uuid.uuid4().hex)
        self._sessions[session.id] = session
        session._task = asyncio.create_task(self._run_login(session))
        logger.info("login_session.started", session_id=session.id)
        return session

    def get(self, session_id: str) -> LoginSession | None:
        return self._sessions.get(session_id)

    async def cancel(self, session_id: str) -> None:
        session = self._sessions.pop(session_id, None)
        if not session:
            return
        session.status = "cancelled"
        if session._task:
            session._task.cancel()
        if session._browser:
            try:
                await session._browser.close()
            except Exception:
                pass
        logger.info("login_session.cancelled", session_id=session_id)

    # ------------------------------------------------------------------
    # Internal: full login flow
    # ------------------------------------------------------------------

    async def _run_login(self, session: LoginSession) -> None:
        log = logger.bind(session_id=session.id)
        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=False,
                    env={"DISPLAY": ":99"},
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-blink-features=AutomationControlled",
                    ],
                )
                session._browser = browser
                log.info("browser.launched")

                context = await browser.new_context(
                    viewport={"width": 1280, "height": 720},
                    locale="en-US",
                    timezone_id="Europe/London",
                    extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
                )
                page = await context.new_page()

                log.info("navigating_to_login")
                await page.goto(INSTAGRAM_LOGIN_URL, wait_until="domcontentloaded")

                logged_in = await self._wait_for_login(session, page, log)
                if not logged_in:
                    log.warning("login_not_completed", status=session.status)
                    await browser.close()
                    return

                # Give Instagram a moment to fully establish the session
                await asyncio.sleep(3)
                current_url = page.url
                log.info("login_detected", url=current_url)

                user_info = await self._extract_user_info(context, page, log)
                storage_state = await context.storage_state()

                account = await self._persist_account(user_info, storage_state, log)

                session.status = "logged_in"
                session.account_summary = {"id": account.id, "username": account.username}
                log.info("login_session.completed", username=account.username, account_id=account.id)

                await browser.close()

        except asyncio.CancelledError:
            log.info("login_session.task_cancelled")
        except Exception as exc:
            session.status = "failed"
            session.error = str(exc)
            log.exception("login_session.failed", error=str(exc))

    async def _wait_for_login(self, session: LoginSession, page, log) -> bool:
        """Poll until the browser URL has left the Instagram login/challenge flow."""
        for tick in range(_LOGIN_TIMEOUT_S // 2):
            if session.status != "waiting":
                return False

            try:
                url = page.url
                parsed = urlparse(url)
                on_instagram = "instagram.com" in parsed.netloc
                in_login_flow = any(parsed.path.startswith(p) for p in _LOGIN_FLOW_PATHS)

                if tick % 15 == 0:  # log every 30 s to avoid noise
                    log.debug("waiting_for_login", url=url, in_login_flow=in_login_flow)

                if on_instagram and not in_login_flow:
                    return True
            except Exception as exc:
                log.debug("url_check_error", error=str(exc))

            await asyncio.sleep(2)

        if session.status == "waiting":
            session.status = "expired"
        return False

    async def _extract_user_info(self, context, page, log) -> dict:
        """Extract IG user info using the authenticated browser context."""

        # Strategy 1: fetch from inside the browser — correct UA + cookies automatically
        try:
            log.info("user_info.trying_browser_fetch")
            data = await page.evaluate("""async () => {
                try {
                    const r = await fetch('/api/v1/accounts/current_user/?edit=true', {
                        headers: {
                            'X-IG-App-ID': '936619743392459',
                            'X-Requested-With': 'XMLHttpRequest',
                        },
                        credentials: 'include',
                    });
                    if (!r.ok) return {_status: r.status, _error: await r.text()};
                    return await r.json();
                } catch(e) {
                    return {_exception: String(e)};
                }
            }""")
            log.info("user_info.browser_fetch_result", result=str(data)[:200] if data else None)
            if data and not data.get("_error") and not data.get("_exception"):
                user = data.get("user", {})
                if user.get("pk"):
                    return {
                        "instagram_user_id": str(user["pk"]),
                        "username": user.get("username", ""),
                        "full_name": user.get("full_name") or None,
                        "profile_pic_url": (
                            user.get("profile_pic_url_hd")
                            or user.get("profile_pic_url")
                            or None
                        ),
                    }
        except Exception as exc:
            log.warning("user_info.browser_fetch_exception", error=str(exc))

        # Strategy 2: context.request with the browser's actual User-Agent header
        try:
            log.info("user_info.trying_context_request")
            user_agent = await page.evaluate("() => navigator.userAgent")
            resp = await context.request.get(
                INSTAGRAM_USER_API,
                headers={
                    "X-IG-App-ID": "936619743392459",
                    "X-Requested-With": "XMLHttpRequest",
                    "User-Agent": user_agent,
                },
            )
            log.info("user_info.context_request_status", status=resp.status)
            if resp.ok:
                data = await resp.json()
                user = data.get("user", {})
                if user.get("pk"):
                    return {
                        "instagram_user_id": str(user["pk"]),
                        "username": user.get("username", ""),
                        "full_name": user.get("full_name") or None,
                        "profile_pic_url": (
                            user.get("profile_pic_url_hd")
                            or user.get("profile_pic_url")
                            or None
                        ),
                    }
            else:
                body = await resp.text()
                log.warning("user_info.context_request_error", status=resp.status, body=body[:200])
        except Exception as exc:
            log.warning("user_info.context_request_exception", error=str(exc))

        # Strategy 3: graphql viewer query (older API, still works on some accounts)
        try:
            log.info("user_info.trying_graphql_viewer")
            data = await page.evaluate("""async () => {
                try {
                    const r = await fetch('/graphql/query/', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                        body: 'doc_id=17846305414581823&variables={}',
                        credentials: 'include',
                    });
                    if (!r.ok) return null;
                    return r.json();
                } catch(e) { return null; }
            }""")
            viewer = (data or {}).get("data", {}).get("viewer", {}).get("actor", {})
            log.info("user_info.graphql_viewer", viewer=str(viewer)[:100] if viewer else None)
            if viewer and viewer.get("username"):
                return {
                    "instagram_user_id": str(viewer.get("id", "")),
                    "username": viewer["username"],
                    "full_name": viewer.get("full_name") or None,
                    "profile_pic_url": viewer.get("profile_pic_url") or None,
                }
        except Exception as exc:
            log.warning("user_info.graphql_exception", error=str(exc))

        # Strategy 4: cookies — ds_user_id gives us the numeric ID, then resolve username
        try:
            log.info("user_info.trying_cookie_fallback")
            storage = await context.storage_state()
            cookies = {
                c["name"]: c["value"]
                for c in storage.get("cookies", [])
                if "instagram.com" in c.get("domain", "")
            }
            log.info("user_info.cookie_names", names=list(cookies.keys()))
            ds_user_id = cookies.get("ds_user_id")
            if ds_user_id:
                # Try to resolve actual username via the user ID
                try:
                    user_data = await page.evaluate(f"""async () => {{
                        try {{
                            const r = await fetch('/api/v1/users/{ds_user_id}/info/', {{
                                headers: {{'X-IG-App-ID': '936619743392459'}},
                                credentials: 'include',
                            }});
                            if (!r.ok) return null;
                            return r.json();
                        }} catch(e) {{ return null; }}
                    }}""")
                    user = (user_data or {}).get("user", {})
                    log.info("user_info.user_lookup", user=str(user)[:100] if user else None)
                    if user and user.get("username"):
                        return {
                            "instagram_user_id": ds_user_id,
                            "username": user["username"],
                            "full_name": user.get("full_name") or None,
                            "profile_pic_url": (
                                user.get("profile_pic_url_hd")
                                or user.get("profile_pic_url")
                                or None
                            ),
                        }
                except Exception as exc:
                    log.warning("user_info.user_lookup_exception", error=str(exc))

                # Last resort: ds_user_id as placeholder (will be corrected on next login)
                log.warning("user_info.using_id_placeholder", ds_user_id=ds_user_id)
                return {
                    "instagram_user_id": ds_user_id,
                    "username": f"user_{ds_user_id}",
                    "full_name": None,
                    "profile_pic_url": None,
                }
        except Exception as exc:
            log.warning("user_info.cookie_fallback_exception", error=str(exc))

        raise RuntimeError(
            "Could not extract user info from Instagram — all strategies failed. "
            "Check container logs for details."
        )

    async def _persist_account(self, user_info: dict, storage_state: dict, log) -> Account:
        """Upsert the account in the database and save the encrypted session file."""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Account).where(
                    Account.instagram_user_id == user_info["instagram_user_id"]
                )
            )
            account = result.scalar_one_or_none()

            if account:
                log.info("account.updating_existing", account_id=account.id)
                account.username = user_info["username"]
                account.display_name = user_info.get("full_name")
                account.profile_pic_url = user_info.get("profile_pic_url")
                account.session_status = "active"
                await db.flush()
            else:
                log.info("account.creating_new", username=user_info["username"])
                account = Account(
                    instagram_user_id=user_info["instagram_user_id"],
                    username=user_info["username"],
                    display_name=user_info.get("full_name"),
                    profile_pic_url=user_info.get("profile_pic_url"),
                    session_path="",
                    session_status="active",
                )
                db.add(account)
                await db.flush()  # get account.id

            session_filename = save_session(account.id, storage_state)
            account.session_path = session_filename
            log.info("session.saved", filename=session_filename, account_id=account.id)

            await db.commit()
            await db.refresh(account)
            return account


login_session_manager = LoginSessionManager()
