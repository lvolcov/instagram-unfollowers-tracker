"""Persist and load Playwright storage state encrypted on disk."""
from __future__ import annotations

import json
from pathlib import Path

from backend.app.core.config import settings
from backend.app.core.security import decrypt_bytes, encrypt_bytes


def save_session(account_id: int, storage_state: dict) -> str:
    """Encrypt and persist a Playwright storage_state dict. Returns the relative path."""
    settings.SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(storage_state).encode()
    encrypted = encrypt_bytes(raw)
    filename = f"account_{account_id}.bin"
    path = settings.SESSIONS_DIR / filename
    path.write_bytes(encrypted)
    return filename


def load_session(filename: str) -> dict:
    """Decrypt and return the stored Playwright storage_state dict."""
    path: Path = settings.SESSIONS_DIR / filename
    encrypted = path.read_bytes()
    raw = decrypt_bytes(encrypted)
    return json.loads(raw)


def cookies_from_storage(storage_state: dict) -> dict[str, str]:
    """Extract the Instagram cookies needed for GraphQL requests."""
    needed = {"sessionid", "ds_user_id", "csrftoken"}
    return {
        c["name"]: c["value"]
        for c in storage_state.get("cookies", [])
        if c.get("name") in needed and c.get("domain", "").endswith("instagram.com")
    }
