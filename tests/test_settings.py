"""Integration tests for the /api/v1/settings endpoints."""
import pytest


pytestmark = pytest.mark.integration


def test_settings_returns_200(client):
    r = client.get("/api/v1/settings")
    assert r.status_code == 200


def test_settings_response_shape(client):
    body = client.get("/api/v1/settings").json()
    required_keys = {
        "timezone",
        "snapshot_retention_days",
        "ha_webhook_url",
        "ha_webhook_id",
        "ha_webhook_enabled",
        "ig_time_between_cycles_ms",
        "ig_time_after_five_cycles_ms",
    }
    assert required_keys.issubset(body.keys())


def test_settings_values_are_correct_types(client):
    body = client.get("/api/v1/settings").json()
    assert isinstance(body["timezone"], str)
    assert isinstance(body["snapshot_retention_days"], int)
    assert isinstance(body["ha_webhook_enabled"], bool)
    assert isinstance(body["ig_time_between_cycles_ms"], int)
    assert isinstance(body["ig_time_after_five_cycles_ms"], int)


def test_webhook_test_returns_result(client):
    """Test webhook endpoint responds (HA may not be reachable, that's okay)."""
    r = client.post("/api/v1/settings/webhook/test")
    assert r.status_code == 200
    body = r.json()
    assert "sent" in body
