"""Shared pytest configuration and fixtures."""
import os
import pytest
import httpx

BASE_URL = os.environ.get("TEST_BASE_URL", "http://localhost:8000")


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "integration: marks tests that require the container to be running (deselect with -m 'not integration')",
    )


@pytest.fixture(scope="session")
def base_url() -> str:
    return BASE_URL


@pytest.fixture(scope="session")
def client(base_url: str) -> httpx.Client:
    with httpx.Client(base_url=base_url, timeout=10.0) as c:
        yield c
