"""Browser-based UI tests using Playwright.

Run with:  python3 -m pytest tests/test_browser.py -v
Screenshots are saved to tests/screenshots/ for visual inspection.

These tests verify:
- Page navigation works correctly
- The Add Account flow opens the noVNC iframe
- No error JSON is shown in the UI
- Key elements are visible and interactive
"""
import os
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

BASE_URL = os.environ.get("TEST_BASE_URL", "http://localhost:8000")
SCREENSHOTS = Path(__file__).parent / "screenshots"
SCREENSHOTS.mkdir(exist_ok=True)

pytestmark = pytest.mark.integration


def shot(page: Page, name: str) -> None:
    """Save a full-page screenshot for visual inspection."""
    page.screenshot(path=str(SCREENSHOTS / f"{name}.png"), full_page=True)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

def test_dashboard_loads(page: Page) -> None:
    page.goto(BASE_URL)
    expect(page).to_have_title("Instagram Unfollowers Tracker")
    shot(page, "01_dashboard")


def test_dashboard_has_header(page: Page) -> None:
    page.goto(BASE_URL)
    # App shell header is visible
    header = page.locator("header, nav").first
    expect(header).to_be_visible()
    shot(page, "02_dashboard_header")


def test_dashboard_has_add_account_button(page: Page) -> None:
    page.goto(BASE_URL)
    # The AccountSwitcher header always shows an aria-label="Add account" link.
    # On an empty dashboard there is also a big "Add Account" CTA — either is fine.
    btn = page.get_by_role("link", name="Add account").or_(
        page.get_by_role("button", name="Add Account")
    ).or_(
        page.get_by_text("Add Account", exact=True)
    ).first
    expect(btn).to_be_visible()
    shot(page, "03_dashboard_add_button")


def test_settings_page_loads(page: Page) -> None:
    page.goto(f"{BASE_URL}/settings")
    expect(page).to_have_url(f"{BASE_URL}/settings")
    # Settings heading
    heading = page.get_by_role("heading", name="Settings")
    expect(heading).to_be_visible()
    shot(page, "04_settings_page")


def test_settings_shows_webhook_config(page: Page) -> None:
    page.goto(f"{BASE_URL}/settings")
    # HA webhook section visible
    page.wait_for_selector("text=Home Assistant", timeout=5000)
    shot(page, "05_settings_webhook_section")


# ---------------------------------------------------------------------------
# Add Account flow
# ---------------------------------------------------------------------------

def test_add_account_page_loads(page: Page) -> None:
    page.goto(f"{BASE_URL}/accounts/add")
    heading = page.get_by_role("heading", name="Add Instagram Account")
    expect(heading).to_be_visible()
    shot(page, "06_add_account_initial")


def test_add_account_open_login_button_visible(page: Page) -> None:
    page.goto(f"{BASE_URL}/accounts/add")
    btn = page.get_by_role("button", name="Open Instagram Login")
    expect(btn).to_be_visible()
    shot(page, "07_add_account_button")


def test_open_instagram_login_shows_iframe(page: Page) -> None:
    """Clicking the button must show an iframe, not an error JSON page."""
    page.goto(f"{BASE_URL}/accounts/add")
    page.get_by_role("button", name="Open Instagram Login").click()

    # Status indicator should appear
    page.wait_for_selector("text=Status:", timeout=8000)
    shot(page, "08_after_click_login_button")

    # iframe must be present and NOT show an error message
    iframe_el = page.locator("iframe[title='Instagram Login']")
    expect(iframe_el).to_be_visible()

    # The page body must not contain raw JSON error text
    page_text = page.inner_text("body")
    assert '"detail": "Not found"' not in page_text, (
        "Page shows raw JSON error — noVNC proxy is not working"
    )
    shot(page, "09_novnc_iframe_visible")


def test_novnc_html_is_reachable(page: Page) -> None:
    """The noVNC vnc.html file must be served (not 404)."""
    resp = page.goto(f"{BASE_URL}/novnc/vnc.html")
    assert resp is not None
    assert resp.status == 200, f"novnc/vnc.html returned {resp.status}"
    shot(page, "10_novnc_html_loaded")


def test_cancel_login_returns_to_dashboard(page: Page) -> None:
    page.goto(f"{BASE_URL}/accounts/add")
    page.get_by_role("button", name="Open Instagram Login").click()
    page.wait_for_selector("text=Status:", timeout=8000)

    page.get_by_role("button", name="Cancel").click()
    # Should navigate back to root/dashboard
    page.wait_for_url(f"{BASE_URL}/", timeout=5000)
    shot(page, "11_after_cancel_dashboard")


# ---------------------------------------------------------------------------
# Client-side routing — deep links must render the SPA, not a 404
# ---------------------------------------------------------------------------

def test_deep_link_does_not_404(page: Page) -> None:
    resp = page.goto(f"{BASE_URL}/accounts/999")
    assert resp is not None
    # SPA serves index.html for unknown account — status 200, React handles the 404
    assert resp.status == 200
    shot(page, "12_deep_link_spa")


def test_unknown_api_route_returns_404_json(page: Page) -> None:
    resp = page.goto(f"{BASE_URL}/api/v1/does-not-exist")
    assert resp is not None
    assert resp.status == 404
    body = page.inner_text("body")
    assert "Not found" in body or "detail" in body
