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

from sqlalchemy import select

from backend.app.core.database import AsyncSessionLocal
from backend.app.instagram.session_store import save_session
from backend.app.models.account import Account


LoginStatus = Literal["waiting", "logged_in", "failed", "expired", "cancelled"]

INSTAGRAM_LOGIN_URL = "https://www.instagram.com/accounts/login/"

# Paths that are part of the login / challenge flow — user is NOT yet logged in
_LOGIN_FLOW_PATHS = (
    "/accounts/login",
    "/challenge",
    "/checkpoint",
    "/accounts/suspended",
)

# How long (seconds) to wait for the user to complete login before timing out
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
        session = LoginSession(id=uuid.uuid4().hex)
        self._sessions[session.id] = session
        session._task = asyncio.create_task(self._run_login(session))
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

    # ------------------------------------------------------------------
    # Internal: run the full login flow
    # ------------------------------------------------------------------

    async def _run_login(self, session: LoginSession) -> None:
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
                    # Suppress the "controlled by automation" infobar
                    extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
                )

                page = await context.new_page()
                await page.goto(INSTAGRAM_LOGIN_URL, wait_until="domcontentloaded")

                # Block until the user successfully logs in (or we time out)
                logged_in = await self._wait_for_login(session, page)

                if not logged_in:
                    return  # status already set by _wait_for_login

                # Give the page a moment to settle after the redirect
                await asyncio.sleep(2)

                user_info = await self._extract_user_info(page)
                storage_state = await context.storage_state()

                account = await self._persist_account(user_info, storage_state)

                session.status = "logged_in"
                session.account_summary = {
                    "id": account.id,
                    "username": account.username,
                }

                await browser.close()

        except asyncio.CancelledError:
            pass
        except Exception as exc:
            session.status = "failed"
            session.error = str(exc)

    async def _wait_for_login(self, session: LoginSession, page) -> bool:
        """
        Poll until:
          - The browser URL has left the Instagram login/challenge flow → True
          - The session is cancelled                                     → False
          - The timeout is reached                                       → False (sets expired)
        """
        for _ in range(_LOGIN_TIMEOUT_S // 2):
            if session.status != "waiting":
                return False

            try:
                url = page.url
                parsed = urlparse(url)
                on_instagram = "instagram.com" in parsed.netloc
                in_login_flow = any(parsed.path.startswith(p) for p in _LOGIN_FLOW_PATHS)

                if on_instagram and not in_login_flow and parsed.path not in ("/", ""):
                    return True
                # Also accept the home feed root
                if on_instagram and parsed.path in ("/", "") and "instagram.com" in parsed.netloc:
                    return True
            except Exception:
                pass  # page navigating, retry

            await asyncio.sleep(2)

        if session.status == "waiting":
            session.status = "expired"
        return False

    async def _extract_user_info(self, page) -> dict:
        """Extract IG user info from an authenticated page session."""
        # Strategy 1: Instagram internal REST API (most reliable)
        try:
            data = await page.evaluate("""async () => {
                const r = await fetch('/api/v1/accounts/current_user/?edit=true', {
                    headers: {
                        'X-IG-App-ID': '936619743392459',
                        'X-Requested-With': 'XMLHttpRequest',
                    },
                    credentials: 'include',
                });
                if (!r.ok) return null;
                const json = await r.json();
                return json.user ?? null;
            }""")
            if data and data.get("pk"):
                return {
                    "instagram_user_id": str(data["pk"]),
                    "username": data.get("username", ""),
                    "full_name": data.get("full_name") or None,
                    "profile_pic_url": data.get("profile_pic_url") or None,
                }
        except Exception:
            pass

        # Strategy 2: window.__additionalDataLoaded / _sharedData
        try:
            viewer = await page.evaluate("""() => {
                const sd = window._sharedData?.config?.viewer;
                if (sd?.id && sd?.username) return sd;
                return null;
            }""")
            if viewer and viewer.get("username"):
                return {
                    "instagram_user_id": str(viewer.get("id", f"uid_{viewer['username']}")),
                    "username": viewer["username"],
                    "full_name": viewer.get("full_name") or None,
                    "profile_pic_url": viewer.get("profile_pic_url") or None,
                }
        except Exception:
            pass

        # Strategy 3: navigate to profile page and scrape username from URL
        try:
            await page.goto("https://www.instagram.com/accounts/edit/", wait_until="domcontentloaded")
            url_after = page.url
            # URL after redirect is typically instagram.com/accounts/edit/
            # but username is sometimes visible in the page title
            title = await page.title()
            # title format: "Edit Profile • Instagram" or "@username • Edit Profile"
            username_from_title = None
            if "@" in title:
                username_from_title = title.split("@")[1].split(" ")[0].strip()
            if username_from_title:
                return {
                    "instagram_user_id": f"uid_{username_from_title}",
                    "username": username_from_title,
                    "full_name": None,
                    "profile_pic_url": None,
                }
        except Exception:
            pass

        raise RuntimeError("Could not extract user info from Instagram — please check your session.")

    async def _persist_account(self, user_info: dict, storage_state: dict) -> Account:
        """Upsert the account in the database and save the encrypted session file."""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Account).where(
                    Account.instagram_user_id == user_info["instagram_user_id"]
                )
            )
            account = result.scalar_one_or_none()

            if account:
                account.username = user_info["username"]
                account.display_name = user_info.get("full_name")
                account.profile_pic_url = user_info.get("profile_pic_url")
                account.session_status = "active"
                await db.flush()
            else:
                account = Account(
                    instagram_user_id=user_info["instagram_user_id"],
                    username=user_info["username"],
                    display_name=user_info.get("full_name"),
                    profile_pic_url=user_info.get("profile_pic_url"),
                    session_path="",  # filled in after flush gives us the ID
                    session_status="active",
                )
                db.add(account)
                await db.flush()  # populate account.id

            # Now we have account.id — save the encrypted session file
            session_filename = save_session(account.id, storage_state)
            account.session_path = session_filename

            await db.commit()
            await db.refresh(account)
            return account


login_session_manager = LoginSessionManager()
