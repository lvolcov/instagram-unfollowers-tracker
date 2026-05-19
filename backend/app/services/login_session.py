"""Manages the single LoginAccount login flow via Playwright + noVNC.

At most one LoginAccount exists at any time. Starting a new login while one is
already saved is rejected — the caller must delete the existing LoginAccount
first (DELETE /api/v1/login-account).
"""
from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal
from urllib.parse import urlparse

import structlog
from sqlalchemy import select

from backend.app.core.database import AsyncSessionLocal
from backend.app.instagram.session_store import save_session
from backend.app.models.login_account import LoginAccount

logger = structlog.get_logger(__name__)

LoginStatus = Literal["waiting", "logged_in", "failed", "expired", "cancelled"]

INSTAGRAM_LOGIN_URL = "https://www.instagram.com/accounts/login/"

_LOGIN_FLOW_PATHS = (
    "/accounts/login",
    "/challenge",
    "/checkpoint",
    "/accounts/suspended",
)

_LOGIN_TIMEOUT_S = 600


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
        # Reject if a LoginAccount already exists.
        async with AsyncSessionLocal() as db:
            existing = await db.execute(select(LoginAccount).limit(1))
            if existing.scalar_one_or_none() is not None:
                raise RuntimeError(
                    "A LoginAccount already exists. Delete it first if you want to log in as a different account."
                )

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

                context = await browser.new_context(
                    viewport={"width": 1280, "height": 720},
                    locale="en-US",
                    timezone_id="Europe/London",
                    extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
                )
                page = await context.new_page()
                await page.goto(INSTAGRAM_LOGIN_URL, wait_until="domcontentloaded")

                logged_in = await self._wait_for_login(session, page, log)
                if not logged_in:
                    await browser.close()
                    return

                await asyncio.sleep(3)
                user_info = await self._extract_user_info(context, page, log)
                storage_state = await context.storage_state()
                account = await self._persist_login_account(user_info, storage_state, log)

                session.status = "logged_in"
                session.account_summary = {"id": account.id, "username": account.username}
                log.info(
                    "login_session.completed",
                    username=account.username,
                    account_id=account.id,
                )

                await browser.close()

        except asyncio.CancelledError:
            log.info("login_session.task_cancelled")
        except Exception as exc:
            session.status = "failed"
            session.error = str(exc)
            log.exception("login_session.failed", error=str(exc))

    async def _wait_for_login(self, session: LoginSession, page, log) -> bool:
        for tick in range(_LOGIN_TIMEOUT_S // 2):
            if session.status != "waiting":
                return False
            try:
                url = page.url
                parsed = urlparse(url)
                on_instagram = "instagram.com" in parsed.netloc
                in_login_flow = any(parsed.path.startswith(p) for p in _LOGIN_FLOW_PATHS)
                if tick % 15 == 0:
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
        """Find username + IG user-id from the freshly-authenticated tab.

        Strategy: read ds_user_id from cookies (always present after login), then
        call /api/v1/users/{ds_user_id}/info/ from inside the browser. The browser
        supplies its own UA so no "useragent mismatch" occurs.
        """
        storage = await context.storage_state()
        cookies = {
            c["name"]: c["value"]
            for c in storage.get("cookies", [])
            if "instagram.com" in c.get("domain", "")
        }
        ds_user_id = cookies.get("ds_user_id")
        if not ds_user_id:
            raise RuntimeError(
                "No ds_user_id cookie after login — Instagram may have shown a checkpoint."
            )

        try:
            data = await page.evaluate(
                """async (uid) => {
                    const r = await fetch('/api/v1/users/' + uid + '/info/', {
                        headers: {'X-IG-App-ID': '936619743392459'},
                        credentials: 'include',
                    });
                    if (!r.ok) return null;
                    return r.json();
                }""",
                ds_user_id,
            )
            user = (data or {}).get("user", {})
            if user and user.get("username"):
                return {
                    "instagram_user_id": ds_user_id,
                    "username": user["username"],
                    "full_name": user.get("full_name") or None,
                    "profile_pic_url": (
                        user.get("profile_pic_url_hd") or user.get("profile_pic_url") or None
                    ),
                }
        except Exception as exc:
            log.warning("user_info.lookup_failed", error=str(exc))

        # Placeholder — at least we still capture the session
        return {
            "instagram_user_id": ds_user_id,
            "username": f"user_{ds_user_id}",
            "full_name": None,
            "profile_pic_url": None,
        }

    async def _persist_login_account(
        self, user_info: dict, storage_state: dict, log
    ) -> LoginAccount:
        async with AsyncSessionLocal() as db:
            # Singleton: delete any existing row before inserting.
            existing = await db.execute(select(LoginAccount))
            for prior in existing.scalars().all():
                await db.delete(prior)

            account = LoginAccount(
                instagram_user_id=user_info["instagram_user_id"],
                username=user_info["username"],
                display_name=user_info.get("full_name"),
                profile_pic_url=user_info.get("profile_pic_url"),
                session_path="",
                session_status="active",
                last_active_at=datetime.now(timezone.utc),
            )
            db.add(account)
            await db.flush()
            account.session_path = save_session(storage_state)
            await db.commit()
            await db.refresh(account)
            log.info("login_account.saved", account_id=account.id, username=account.username)
            return account


login_session_manager = LoginSessionManager()
