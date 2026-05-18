"""Integration tests for the /api/v1/accounts endpoints."""
import pytest


pytestmark = pytest.mark.integration


def test_list_accounts_returns_list(client):
    r = client.get("/api/v1/accounts")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_get_nonexistent_account_returns_404(client):
    r = client.get("/api/v1/accounts/99999")
    assert r.status_code == 404


def test_delete_nonexistent_account_returns_404(client):
    r = client.delete("/api/v1/accounts/99999")
    assert r.status_code == 404


def test_reauth_nonexistent_account_returns_404(client):
    r = client.post("/api/v1/accounts/99999/reauth")
    assert r.status_code == 404


def test_login_start_returns_session(client):
    """Auth start endpoint returns a session_id and a noVNC URL."""
    r = client.post("/api/v1/auth/login/start")
    assert r.status_code == 200
    body = r.json()
    assert "session_id" in body
    assert "novnc_url" in body


def test_login_status_unknown_session(client):
    r = client.get("/api/v1/auth/login/status/nonexistent-session-id")
    assert r.status_code in (200, 404)
    if r.status_code == 200:
        assert r.json()["status"] in ("not_found", "failed", "waiting")


def test_cancel_unknown_session(client):
    r = client.post("/api/v1/auth/login/cancel/nonexistent-session-id")
    assert r.status_code in (200, 404)
