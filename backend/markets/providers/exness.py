"""Read-only Exness Trader API client.

This module intentionally exposes GET operations only. It has no order,
position mutation, or trade execution methods.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
import os
import re
import time
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone
from urllib.parse import urlsplit

import httpx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


logger = logging.getLogger(__name__)


class ExnessConfigurationError(RuntimeError):
    pass


class ExnessAPIError(RuntimeError):
    pass


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ExnessConfigurationError(f"Missing required environment variable: {name}")
    return value


def _base_url(value: str) -> str:
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
        raise ExnessConfigurationError(
            "Exness hosts must be HTTPS origins without credentials, paths, queries or fragments."
        )
    # Exness documents the Gateway and account Access Point as values supplied
    # by Key Management / discovery, not as fixed hostnames. Do not hardcode
    # example domains; redirects are disabled before any signed request.
    return f"https://{parsed.netloc}"


def _load_private_key(value: str) -> Ed25519PrivateKey:
    text = value.strip()
    if text.startswith("-----BEGIN PRIVATE KEY-----"):
        key = serialization.load_pem_private_key(text.encode(), password=None)
        if not isinstance(key, Ed25519PrivateKey):
            raise ExnessConfigurationError("EXN_PRIVATE_KEY must be an Ed25519 private key.")
        return key
    if not re.fullmatch(r"[0-9a-fA-F]{128}", text):
        raise ExnessConfigurationError(
            "EXN_PRIVATE_KEY must be 128 hex characters or an unencrypted PKCS#8 PEM key."
        )
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
        self._request_lock = asyncio.Lock()
        self._next_request_at = 0.0
        self._rate_limited_until = 0.0
        self._rate_limit_streak = 0
        self._min_request_interval = max(0.25, min(10.0, float(os.getenv("EXN_MIN_REQUEST_INTERVAL_SECONDS", "1.0"))))

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
        async with self._request_lock:
            now = time.monotonic()
            if now < self._rate_limited_until:
                remaining = max(1, int(self._rate_limited_until - now))
                raise ExnessAPIError(f"Exness rate-limit cooldown active; retry in approximately {remaining}s (HTTP 429).")
            wait_for_slot = self._next_request_at - now
            if wait_for_slot > 0:
                await asyncio.sleep(wait_for_slot)
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=False) as client:
                response = await client.get(host + path_with_query, headers=self._signed_get_headers(path_with_query))
            completed_at = time.monotonic()
            self._next_request_at = completed_at + self._min_request_interval
            if response.status_code == 429:
                self._rate_limit_streak = min(self._rate_limit_streak + 1, 4)
                backoff = min(300.0, 60.0 * (2 ** (self._rate_limit_streak - 1)))
                retry_after = response.headers.get("Retry-After")
                if retry_after:
                    try:
                        backoff = max(backoff, min(900.0, float(retry_after)))
                    except ValueError:
                        try:
                            retry_at = parsedate_to_datetime(retry_after)
                            if retry_at.tzinfo is None:
                                retry_at = retry_at.replace(tzinfo=timezone.utc)
                            backoff = max(backoff, min(900.0, (retry_at - datetime.now(timezone.utc)).total_seconds()))
                        except (TypeError, ValueError, OverflowError):
                            pass
                self._rate_limited_until = completed_at + max(1.0, backoff)
                logger.warning("exness_rate_limit_cooldown seconds=%s streak=%s", int(self._rate_limited_until - completed_at), self._rate_limit_streak)
            elif response.status_code < 400:
                self._rate_limit_streak = 0
        if response.is_redirect:
            raise ExnessAPIError("Exness returned a redirect; signed credentials were not forwarded.")
        if response.status_code == 429:
            remaining = max(1, int(self._rate_limited_until - time.monotonic()))
            raise ExnessAPIError(f"Exness API returned HTTP 429; cooldown {remaining}s.")
        if response.status_code >= 400:
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


    async def get_candles(
        self, instrument: str, timeframe: str = "M15", count: int = 100, price_type: str = "both"
    ) -> list[dict]:
        """Read historical bid/ask candles; this method cannot mutate account state."""
        from datetime import datetime, timedelta, timezone
        from urllib.parse import urlencode

        allowed_timeframes = {"S1", "S5", "S15", "M1", "M3", "M5", "M10", "M15", "M30", "H1", "H2", "H4", "D1", "W1", "MN"}
        if instrument not in {"XAUUSD", "EURUSD", "GBPUSD"}:
            raise ExnessConfigurationError("Instrument is not enabled for the initial Exness market-data rollout.")
        if timeframe not in allowed_timeframes:
            raise ExnessConfigurationError("Unsupported Exness candle timeframe.")
        if not 1 <= count <= 500:
            raise ExnessConfigurationError("Candle count must be between 1 and 500.")
        if price_type not in {"bid", "ask", "both"}:
            raise ExnessConfigurationError("Candle price_type must be bid, ask or both.")
        seconds = {"S1": 1, "S5": 5, "S15": 15, "M1": 60, "M3": 180, "M5": 300, "M10": 600, "M15": 900, "M30": 1800, "H1": 3600, "H2": 7200, "H4": 14400, "D1": 86400, "W1": 604800, "MN": 2592000}[timeframe]
        # Exness count is bidirectional: a negative value backfills candles
        # before `from`. Anchor at now so closed-market gaps do not consume
        # the requested history window (e.g. weekends for M15/H1).
        anchor = datetime.now(timezone.utc)
        query = urlencode({
            "instrument": instrument,
            "timeframe": timeframe,
            "from": anchor.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "count": -count,
            "price_type": price_type,
        })
        access_point = await self.discover_access_point()
        result = await self._get_json(
            access_point,
            f"/v1/market-data/accounts/{self.account_id}/candles?{query}",
        )
        candles = result.get("candles")
        if not isinstance(candles, list):
            raise ExnessAPIError("Exness returned an invalid candle history response.")
        return candles

    async def get_ticks(self, instruments: list[str]) -> list[dict]:
        """Open one signed read-only WebSocket subscription and collect initial ticks."""
        import asyncio
        import websockets

        allowed = {"XAUUSD", "EURUSD", "GBPUSD"}
        if not instruments or len(instruments) > 3 or any(item not in allowed for item in instruments):
            raise ExnessConfigurationError("Only XAUUSD, EURUSD and GBPUSD are enabled for initial tick streaming.")
        access_point = await self.discover_access_point()
        path = f"/v1/server-events/accounts/{self.account_id}/ws/ticks"
        headers = self._signed_get_headers(path)
        ws_url = "wss://" + access_point.removeprefix("https://") + path
        ticks: dict[str, dict] = {}
        try:
            async with websockets.connect(
                ws_url, additional_headers=headers, open_timeout=12, close_timeout=2,
                ping_interval=20, ping_timeout=20, compression=None,
                subprotocols=["exness-ws-protocol"],
            ) as socket:
                await socket.send(json.dumps({
                    "id": "vantage-point-initial-ticks",
                    "subscribe": {"event": "ticks", "instruments": instruments},
                }))
                deadline = asyncio.get_running_loop().time() + 12
                while set(ticks) != set(instruments):
                    remaining = deadline - asyncio.get_running_loop().time()
                    if remaining <= 0:
                        break
                    try:
                        message = await asyncio.wait_for(socket.recv(), timeout=remaining)
                    except asyncio.TimeoutError:
                        # Exness can deliver a valid initial tick for one
                        # instrument while another subscribed symbol has no
                        # quote. Preserve the ticks already received instead
                        # of discarding the whole snapshot on the final timeout.
                        break
                    event = json.loads(message)
                    if not isinstance(event, dict):
                        continue
                    # Exness reports subscription failures as structured messages
                    # without an instrument field. Surface those immediately instead
                    # of silently waiting until the initial-tick timeout.
                    # Exness sends a successful subscription acknowledgement as
                    # {"id": "<request id>", "code": 200}. It is not a tick and
                    # must not be mistaken for a REQUEST_INVALID error.
                    if event.get("code") == 200 and "instrument" not in event:
                        continue
                    if "error_message" in event or (
                        "code" in event and "instrument" not in event
                    ):
                        error_code = event.get("code")
                        error_message = event.get("error_message")
                        if isinstance(error_message, str) and error_message:
                            error_message = re.sub(r"[^A-Z0-9_ -]", "", error_message.upper())[:80]
                        else:
                            error_message = f"ERROR_CODE_{error_code}"
                        raise ExnessAPIError(
                            f"Exness rejected tick subscription (code={error_code}, reason={error_message})."
                        )
                    symbol = event.get("instrument")
                    if symbol not in instruments:
                        continue
                    bid, ask = event.get("bid"), event.get("ask")
                    if not isinstance(bid, (int, float)) or not isinstance(ask, (int, float)) or bid <= 0 or ask < bid:
                        continue
                    ticks[symbol] = {
                        "instrument": symbol, "bid": bid, "ask": ask,
                        "timestamp": event.get("timestamp"), "provider": "exness",
                    }
        except Exception as exc:
            if isinstance(exc, (ExnessConfigurationError, ExnessAPIError)):
                raise
            # websockets.InvalidStatus exposes the HTTP response on handshake
            # failures; ConnectionClosed exposes a close code/reason. Keep these
            # diagnostics credential-free and avoid logging headers or response bodies.
            response = getattr(exc, "response", None)
            status = getattr(response, "status_code", None)
            close_code = getattr(exc, "code", None)
            close_reason = getattr(exc, "reason", None)
            logger.warning(
                "exness_ticks_ws_failed error_type=%s error_detail=%s http_status=%s close_code=%s close_reason=%s",
                type(exc).__name__,
                re.sub(r"[^A-Za-z0-9_ .,=:-]", "", str(exc))[:160],
                status, close_code,
                str(close_reason)[:120] if close_reason is not None else None,
            )
            if status is not None:
                detail = f"Exness WebSocket handshake rejected (HTTP {status})."
            elif close_code is not None:
                detail = f"Exness WebSocket closed (code={close_code}, reason={str(close_reason)[:80]})."
            elif isinstance(exc, (asyncio.TimeoutError, TimeoutError)):
                detail = "Exness WebSocket timed out waiting for initial ticks."
            else:
                safe_detail = re.sub(r"[^A-Za-z0-9_ .,=:-]", "", str(exc))[:120]
                detail = f"Exness WebSocket failed ({type(exc).__name__}: {safe_detail})."
            raise ExnessAPIError(detail) from exc
        if not ticks:
            raise ExnessAPIError(
                "Exness returned no initial ticks for the requested instruments "
                f"within the subscription window ({', '.join(instruments)})."
            )
        missing = sorted(set(instruments) - set(ticks))
        if missing:
            logger.warning(
                "exness_ticks_initial_partial received=%s missing=%s",
                sorted(ticks), missing,
            )
        return [ticks[symbol] for symbol in instruments if symbol in ticks]
