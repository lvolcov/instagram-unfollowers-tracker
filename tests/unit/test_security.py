"""Unit tests for the Fernet encryption helpers."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import pytest
from cryptography.fernet import Fernet, InvalidToken


os.environ.setdefault("SECRET_KEY", Fernet.generate_key().decode())
os.environ.setdefault("HA_WEBHOOK_URL", "http://localhost:8123")
os.environ.setdefault("HA_WEBHOOK_ID", "test")

from backend.app.core.security import encrypt_str, decrypt_str, encrypt_bytes, decrypt_bytes


def test_encrypt_decrypt_str_roundtrip():
    original = "my secret session token"
    assert decrypt_str(encrypt_str(original)) == original


def test_encrypt_decrypt_bytes_roundtrip():
    original = b"\x00\x01\x02\xff some binary data"
    assert decrypt_bytes(encrypt_bytes(original)) == original


def test_encrypted_str_is_different_from_original():
    original = "plaintext"
    assert encrypt_str(original) != original


def test_encrypted_str_is_base64_like():
    encrypted = encrypt_str("hello")
    assert isinstance(encrypted, str)
    assert len(encrypted) > 10


def test_tampered_token_raises():
    token = encrypt_str("data")
    tampered = token[:-5] + "XXXXX"
    with pytest.raises(Exception):
        decrypt_str(tampered)


def test_empty_string_roundtrip():
    assert decrypt_str(encrypt_str("")) == ""


def test_unicode_roundtrip():
    original = "こんにちは 🎉 special chars: <>&\""
    assert decrypt_str(encrypt_str(original)) == original
