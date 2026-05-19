"""Browser-based UI tests using Playwright.

Run with:  python3 -m pytest tests/test_browser.py -v
Screenshots are saved to tests/screenshots/ for visual inspection.
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
    page.screenshot(path=str(SCREENSHOTS / f"{name}.png"), full_page=True)


def test_dashboard_loads(page: Page) -> None:
    page.goto(BASE_URL)
    expect(page).to_have_title("Instagram Unfollowers Tracker")
    shot(page, "01_dashboard")


def test_sidebar_brand_visible(page: Page) -> None:
    page.goto(BASE_URL)
    brand = page.get_by_text("Unfollowers", exact=True).first
    expect(brand).to_be_visible()
    shot(page, "02_sidebar_brand")


def test_dashboard_shows_login_cta_or_tracked(page: Page) -> None:
    """Either an empty 'Log in' CTA, or the 'Logged in as' banner is visible."""
    page.goto(BASE_URL)
    page.wait_for_load_state("networkidle")
    text = page.inner_text("body")
    assert ("Log in" in text) or ("Logged in as" in text)
    shot(page, "03_dashboard_state")


def test_settings_page_loads(page: Page) -> None:
    page.goto(f"{BASE_URL}/settings")
    expect(page).to_have_url(f"{BASE_URL}/settings")
    heading = page.get_by_role("heading", name="Settings")
    expect(heading).to_be_visible()
    shot(page, "04_settings_page")


def test_settings_shows_webhook_config(page: Page) -> None:
    page.goto(f"{BASE_URL}/settings")
    page.wait_for_selector("text=Home Assistant", timeout=5000)
    shot(page, "05_settings_webhook_section")


def test_login_page_loads(page: Page) -> None:
    page.goto(f"{BASE_URL}/login")
    expect(page.get_by_role("heading", name="Log in to Instagram")).to_be_visible()
    shot(page, "06_login_initial")


def test_login_button_visible(page: Page) -> None:
    page.goto(f"{BASE_URL}/login")
    page.wait_for_load_state("networkidle")
    # If a LoginAccount already exists we'll see the warning instead of the button.
    text = page.inner_text("body")
    assert ("Open Instagram login" in text) or ("Already logged in" in text)
    shot(page, "07_login_button_or_existing")


def test_legacy_accounts_add_redirects_to_login(page: Page) -> None:
    page.goto(f"{BASE_URL}/accounts/add")
    page.wait_for_url(f"{BASE_URL}/login", timeout=5000)
    shot(page, "08_legacy_redirect")


def test_novnc_html_is_reachable(page: Page) -> None:
    resp = page.goto(f"{BASE_URL}/novnc/vnc.html")
    assert resp is not None
    assert resp.status == 200, f"novnc/vnc.html returned {resp.status}"
    shot(page, "09_novnc_html_loaded")


def test_deep_link_does_not_404(page: Page) -> None:
    resp = page.goto(f"{BASE_URL}/accounts/999")
    assert resp is not None
    assert resp.status == 200
    shot(page, "10_deep_link_spa")


def test_unknown_api_route_returns_404_json(page: Page) -> None:
    resp = page.goto(f"{BASE_URL}/api/v1/does-not-exist")
    assert resp is not None
    assert resp.status == 404
    body = page.inner_text("body")
    assert "Not found" in body or "detail" in body
