import base64
import hashlib
import json
import os
import time

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from markets.providers.exness import ExnessReadOnlyClient, _base_url, _load_private_key


def test_exness_base_url_rejects_non_https_and_non_exness_hosts():
    with pytest.raises(Exception):
        _base_url("http://api.exness.com")
    with pytest.raises(Exception):
        _base_url("https://example.com")


def test_exness_base_url_accepts_exness_host():
    assert _base_url("https://gateway.example.exness.com/") == "https://gateway.example.exness.com"


def test_load_generated_hex_ed25519_key():
    key = Ed25519PrivateKey.generate()
    seed = key.private_bytes(
        serialization.Encoding.Raw,
        serialization.PrivateFormat.Raw,
        serialization.NoEncryption(),
    )
    public = key.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )
    loaded = _load_private_key((seed + public).hex())
    assert isinstance(loaded, Ed25519PrivateKey)


def test_signed_get_headers_are_signed_get_and_have_empty_idempotency(monkeypatch):
    key = Ed25519PrivateKey.generate()
    seed = key.private_bytes(
        serialization.Encoding.Raw,
        serialization.PrivateFormat.Raw,
        serialization.NoEncryption(),
    )
    public = key.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )
    monkeypatch.setenv("EXN_API_KEY", "exnsk-test")
    monkeypatch.setenv("EXN_PRIVATE_KEY", (seed + public).hex())
    monkeypatch.setenv("EXN_ACCOUNT_ID", "123456")
    monkeypatch.setenv("EXN_DISCOVERY_BASE_URL", "https://gateway.exness.com")
    monkeypatch.setenv("EXN_READ_ONLY", "true")
    client = ExnessReadOnlyClient()
    path = "/v1/trading/access-point?account_id=123456"
    headers = client._signed_get_headers(path)
    payload = json.loads(base64.urlsafe_b64decode(headers["EXN-DATA"] + "=="))
    assert payload["method"] == "GET"
    assert payload["path"] == path
    assert payload["idempotency_key"] == ""
    assert headers["EXN-IDEMPOTENCY-KEY"] == ""
    assert payload["body_hash"] == base64.urlsafe_b64encode(hashlib.sha256(b"").digest()).decode().rstrip("=")
    signature = base64.urlsafe_b64decode(headers["EXN-SIGN"] + "==")
    client.private_key.public_key().verify(signature, base64.urlsafe_b64decode(headers["EXN-DATA"] + "=="))


def test_client_refuses_non_readonly_mode(monkeypatch):
    monkeypatch.setenv("EXN_READ_ONLY", "false")
    with pytest.raises(Exception):
        ExnessReadOnlyClient()
