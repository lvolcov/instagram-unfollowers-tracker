"""Smoke tests: container is up, port is open, and basic endpoints respond."""
import pytest


pytestmark = pytest.mark.integration


def test_health_status_ok(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200


def test_health_response_shape(client):
    body = client.get("/api/v1/health").json()
    assert body["status"] == "ok"
    assert "version" in body
    assert isinstance(body["uptime_seconds"], int)
    assert body["uptime_seconds"] >= 0


def test_frontend_served(client):
    """React SPA is built and served at the root."""
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "<html" in r.text


def test_openapi_docs_available(client):
    r = client.get("/api/openapi.json")
    assert r.status_code == 200
    spec = r.json()
    assert spec["info"]["title"] == "Instagram Unfollowers Tracker"


def test_api_404_for_unknown_route(client):
    r = client.get("/api/v1/does-not-exist")
    assert r.status_code == 404
