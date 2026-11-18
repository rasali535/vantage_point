import base64
import hashlib
import json

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from markets.providers.exness import ExnessConfigurationError, ExnessReadOnlyClient, _base_url, _load_private_key


def test_exness_base_url_rejects_non_https_and_non_origin_urls():
    for value in (
        "http://gateway.example",
        "https://user:pass@gateway.example",
        "https://gateway.example/path",
        "https://gateway.example/?query=1",
        "https://gateway.example/#fragment",
    ):
        with pytest.raises(ExnessConfigurationError):
            _base_url(value)


def test_exness_base_url_accepts_gateway_and_discovered_access_point_hosts():
    assert _base_url("https://gateway.example/") == "https://gateway.example"
    assert _base_url("https://access-point.example") == "https://access-point.example"


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


def test_signed_get_headers_match_exness_documented_shape(monkeypatch):
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
    monkeypatch.setenv("EXN_DISCOVERY_BASE_URL", "https://gateway.example")
    monkeypatch.setenv("EXN_READ_ONLY", "true")
    client = ExnessReadOnlyClient()
    path = "/v1/trading/access-point?account_id=123456"
    headers = client._signed_get_headers(path)
    encoded_payload = headers["EXN-DATA"]
    payload_bytes = base64.urlsafe_b64decode(encoded_payload + "=" * (-len(encoded_payload) % 4))
    payload = json.loads(payload_bytes)
    assert payload["method"] == "GET"
    assert payload["path"] == path
    assert payload["idempotency_key"] == ""
    assert headers["EXN-IDEMPOTENCY-KEY"] == ""
    assert payload["body_hash"] == "47DEQpj8HBSa-_TImW-5JCeuQeRkm5NMpJWZG3hSuFU"
    signature = base64.urlsafe_b64decode(
        headers["EXN-SIGN"] + "=" * (-len(headers["EXN-SIGN"]) % 4)
    )
    client.private_key.public_key().verify(signature, payload_bytes)


def test_client_refuses_non_readonly_mode(monkeypatch):
    monkeypatch.setenv("EXN_READ_ONLY", "false")
    with pytest.raises(ExnessConfigurationError):
        ExnessReadOnlyClient()
