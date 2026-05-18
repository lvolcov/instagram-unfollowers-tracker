"""Encryption helpers for storing Instagram session state at rest."""
from cryptography.fernet import Fernet

from backend.app.core.config import settings


def _get_fernet() -> Fernet:
    key = settings.SECRET_KEY.encode()
    return Fernet(key)


def encrypt_bytes(data: bytes) -> bytes:
    return _get_fernet().encrypt(data)


def decrypt_bytes(token: bytes) -> bytes:
    return _get_fernet().decrypt(token)


def encrypt_str(data: str) -> str:
    return encrypt_bytes(data.encode()).decode()


def decrypt_str(token: str) -> str:
    return decrypt_bytes(token.encode()).decode()
