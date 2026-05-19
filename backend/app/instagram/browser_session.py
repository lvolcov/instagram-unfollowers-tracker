"""Spin up a short-lived Playwright tab pre-loaded with the LoginAccount session.

Used by the scan service (and any other code that needs to make IG calls from
inside a real browser). The context manager opens Chromium on the Xvfb display,
restores the saved storage_state, navigates to instagram.com so cookies + page
context warm up, then hands a `BrowserIGClient` to the caller. On exit the
browser is torn down.
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

import structlog
from playwright.async_api import async_playwright

from backend.app.instagram.client import BrowserIGClient
from backend.app.instagram.session_store import load_session

logger = structlog.get_logger(__name__)

_LAUNCH_ARGS = [
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-dev-shm-usage",
    "--disable-blink-features=AutomationControlled",
]


@asynccontextmanager
async def open_logged_in_page(session_path: str):
    """Yield a `BrowserIGClient` backed by a real instagram.com tab."""
    storage = load_session(session_path)
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            env={"DISPLAY": ":99"},
            args=_LAUNCH_ARGS,
        )
        try:
            context = await browser.new_context(
                storage_state=storage,
                viewport={"width": 1280, "height": 720},
                locale="en-US",
                timezone_id="Europe/London",
                extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
            )
            page = await context.new_page()
            logger.info("browser_session.navigating_home")
            await page.goto("https://www.instagram.com/", wait_until="domcontentloaded")
            # Brief settle — let Instagram's JS attach its session
            await asyncio.sleep(2)
            yield BrowserIGClient(page)
        finally:
            try:
                await browser.close()
            except Exception:
                pass
