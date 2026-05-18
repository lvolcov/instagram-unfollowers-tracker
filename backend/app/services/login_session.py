"""Manages in-flight Instagram login sessions backed by Playwright + noVNC.

Each session spawns a Chromium window inside the container's Xvfb display.
The browser is visible via noVNC (websockify proxies VNC → WebSocket → web UI).
Once login succeeds (detected by URL transition), the storage state is saved
and the account is persisted in the DB.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Literal


LoginStatus = Literal["waiting", "logged_in", "failed", "expired", "cancelled"]


@dataclass
class LoginSession:
    id: str
    status: LoginStatus = "waiting"
    account_summary: dict | None = None
    error: str | None = None
    _browser_pid: int | None = field(default=None, repr=False)


class LoginSessionManager:
    """In-memory registry of active Playwright/noVNC login sessions.

    TODO (Phase 1):
    - Spawn Playwright with persistent context pointing at /app/data/sessions/<sid>
    - Watch URL transitions to detect successful login
    - Extract IG user ID + username from /accounts/edit or graphql
    - Encrypt and persist storage state
    - Create Account row in DB
    """

    def __init__(self) -> None:
        self._sessions: dict[str, LoginSession] = {}

    async def start(self) -> LoginSession:
        session = LoginSession(id=uuid.uuid4().hex)
        self._sessions[session.id] = session
        # TODO: launch Playwright browser bound to DISPLAY=:99
        return session

    def get(self, session_id: str) -> LoginSession | None:
        return self._sessions.get(session_id)

    async def cancel(self, session_id: str) -> None:
        session = self._sessions.pop(session_id, None)
        if session:
            session.status = "cancelled"
            # TODO: kill Playwright browser process


login_session_manager = LoginSessionManager()
