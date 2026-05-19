"""Integration tests for the singleton /api/v1/login-account and /tracked-accounts routes."""
import pytest

pytestmark = pytest.mark.integration


def test_login_account_returns_null_or_object(client):
    r = client.get("/api/v1/login-account")
    assert r.status_code == 200
    body = r.json()
    assert body is None or isinstance(body, dict)


def test_delete_login_account_without_session_returns_404(client):
    # If a session has been set up manually this may succeed (200); we tolerate either.
    r = client.delete("/api/v1/login-account")
    assert r.status_code in (200, 404)


def test_list_tracked_accounts_returns_list(client):
    r = client.get("/api/v1/tracked-accounts")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_get_nonexistent_tracked_returns_404(client):
    r = client.get("/api/v1/tracked-accounts/99999")
    assert r.status_code == 404


def test_delete_nonexistent_tracked_returns_404(client):
    r = client.delete("/api/v1/tracked-accounts/99999")
    assert r.status_code == 404


def test_add_tracked_without_login_returns_400(client):
    """Without a logged-in account, adding a tracked account should be rejected."""
    # Only run when no login is configured
    existing = client.get("/api/v1/login-account").json()
    if existing is not None:
        pytest.skip("LoginAccount exists — this test only runs from a clean state")
    r = client.post("/api/v1/tracked-accounts", json={"username": "instagram"})
    assert r.status_code == 400


def test_login_start_without_existing_returns_session_or_409(client):
    """Either we start a new session (200) or one already exists (409)."""
    r = client.post("/api/v1/auth/login/start")
    assert r.status_code in (200, 409)
    if r.status_code == 200:
        body = r.json()
        assert "session_id" in body and "novnc_url" in body
        # Always cancel to free the Xvfb display for other tests.
        client.post(f"/api/v1/auth/login/cancel/{body['session_id']}")


def test_login_status_unknown_session_returns_404(client):
    r = client.get("/api/v1/auth/login/status/nonexistent-session-id")
    assert r.status_code == 404


def test_cancel_unknown_session_is_safe(client):
    r = client.post("/api/v1/auth/login/cancel/nonexistent-session-id")
    assert r.status_code == 200
