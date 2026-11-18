"""Read-only Exness Trader API client.

This module intentionally exposes GET operations only. It has no order,
position mutation, or trade execution methods.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import time
from urllib.parse import urlsplit

import httpx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


class ExnessConfigurationError(RuntimeError):
    pass


class ExnessAPIError(RuntimeError):
    pass


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ExnessConfigurationError(f"Missing required environment variable: {name}")
    return value


def _base_url(value: str, *, allow_gateway_host: bool = False) -> str:
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.path not in ("", "/")
        or parsed.query
        or parsed.fragment
    ):
        raise ExnessConfigurationError("Exness hosts must be HTTPS origins without credentials, paths, queries or fragments.")
    hostname = (parsed.hostname or "").lower()
    if not (hostname == "exness.com" or hostname.endswith(".exness.com")):
        raise ExnessConfigurationError("Exness API host is not within the official exness.com domain.")
    return f"https://{parsed.netloc}"


def _load_private_key(value: str) -> Ed25519PrivateKey:
    text = value.strip()
    if text.startswith("-----BEGIN PRIVATE KEY-----"):
        key = serialization.load_pem_private_key(text.encode(), password=None)
        if not isinstance(key, Ed25519PrivateKey):
            raise ExnessConfigurationError("EXN_PRIVATE_KEY must be an Ed25519 private key.")
        return key
    if not re.fullmatch(r"[0-9a-fA-F]{128}", text):
        raise ExnessConfigurationError("EXN_PRIVATE_KEY must be 128 hex characters or an unencrypted PKCS#8 PEM key.")
    raw = bytes.fromhex(text)
    key = Ed25519PrivateKey.from_private_bytes(raw[:32])
    public = key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    if public != raw[32:]:
        raise ExnessConfigurationError("EXN_PRIVATE_KEY public half does not match its seed.")
    return key


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


class ExnessReadOnlyClient:
    """Trader API client restricted to signed HTTP GET requests."""

    def __init__(self) -> None:
        if os.getenv("EXN_READ_ONLY", "true").strip().lower() != "true":
            raise ExnessConfigurationError("Exness integration requires EXN_READ_ONLY=true.")
        self.api_key = _required_env("EXN_API_KEY")
        self.account_id = _required_env("EXN_ACCOUNT_ID")
        if not re.fullmatch(r"[1-9][0-9]{0,19}", self.account_id) or int(self.account_id) > 2**64 - 1:
            raise ExnessConfigurationError("EXN_ACCOUNT_ID must be a positive uint64 decimal string.")
        self.gateway = _base_url(_required_env("EXN_DISCOVERY_BASE_URL"))
        self.private_key = _load_private_key(_required_env("EXN_PRIVATE_KEY"))
        self._access_point: str | None = None

    def _signed_get_headers(self, path_with_query: str) -> dict[str, str]:
        timestamp = int(time.time() * 1000)
        payload = json.dumps(
            {
                "api_key": self.api_key,
                "idempotency_key": "",
                "timestamp": timestamp,
                "sign_version": 1,
                "method": "GET",
                "path": path_with_query,
                "body_hash": _b64url(hashlib.sha256(b"").digest()),
            },
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        return {
            "EXN-API-KEY": self.api_key,
            "EXN-IDEMPOTENCY-KEY": "",
            "EXN-TIMESTAMP": str(timestamp),
            "EXN-SIGN-VERSION": "1",
            "EXN-DATA": _b64url(payload),
            "EXN-SIGN": _b64url(self.private_key.sign(payload)),
            "Accept": "application/json",
        }

    async def _get_json(self, host: str, path_with_query: str) -> dict:
        if not path_with_query.startswith("/") or path_with_query.startswith("//"):
            raise ExnessConfigurationError("Invalid Exness API path.")
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=False) as client:
            response = await client.get(
                host + path_with_query,
                headers=self._signed_get_headers(path_with_query),
            )
        if response.is_redirect:
            raise ExnessAPIError("Exness returned a redirect; signed credentials were not forwarded.")
        if response.status_code >= 400:
            # Do not include response bodies: they may contain account or request details.
            raise ExnessAPIError(f"Exness API returned HTTP {response.status_code}.")
        try:
            data = response.json()
        except ValueError as exc:
            raise ExnessAPIError("Exness API returned a non-JSON response.") from exc
        if not isinstance(data, dict):
            raise ExnessAPIError("Exness API returned an unexpected response format.")
        return data

    async def discover_access_point(self) -> str:
        if self._access_point:
            return self._access_point
        discovery = await self._get_json(
            self.gateway,
            f"/v1/trading/access-point?account_id={self.account_id}",
        )
        value = discovery.get("access_point")
        if not isinstance(value, str) or not value:
            raise ExnessAPIError("Exness discovery response did not include an access point.")
        self._access_point = _base_url(value)
        return self._access_point

    async def get_account(self) -> dict:
        access_point = await self.discover_access_point()
        return await self._get_json(
            access_point,
            f"/v1/configuration/accounts/{self.account_id}/account",
        )

    async def get_instruments(self) -> list[str]:
        access_point = await self.discover_access_point()
        result = await self._get_json(
            access_point,
            f"/v1/configuration/accounts/{self.account_id}/instruments",
        )
        instruments = result.get("instruments")
        if not isinstance(instruments, list) or any(not isinstance(item, str) for item in instruments):
            raise ExnessAPIError("Exness returned an invalid instrument list.")
        return instruments
