"""Encrypted persistence of the (single) LoginAccount's Playwright storage_state."""
from __future__ import annotations

import json

from backend.app.core.config import settings
from backend.app.core.security import decrypt_bytes, encrypt_bytes

_FILENAME = "login_account.bin"


def save_session(storage_state: dict) -> str:
    """Encrypt and persist storage_state for the single LoginAccount."""
    settings.SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(storage_state).encode()
    path = settings.SESSIONS_DIR / _FILENAME
    path.write_bytes(encrypt_bytes(raw))
    return _FILENAME


def load_session(filename: str = _FILENAME) -> dict:
    path = settings.SESSIONS_DIR / filename
    return json.loads(decrypt_bytes(path.read_bytes()))


def delete_session(filename: str = _FILENAME) -> None:
    path = settings.SESSIONS_DIR / filename
    if path.exists():
        path.unlink()
