"""Read-only Twelve Data adapter used to verify external FX/metals market data.

This module only performs public market-data GET requests. It has no broker,
account, order, position, or paper-ledger dependencies.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

BASE_URL = "https://api.twelvedata.com"
SYMBOLS = {"XAU/USD", "EUR/USD", "GBP/USD"}
INTERVALS = {"15min": 15, "1h": 60}


class TwelveDataConfigurationError(RuntimeError):
    """The provider is not configured correctly."""


class TwelveDataAPIError(RuntimeError):
    """The provider rejected a request or returned unusable data."""


def _decimal(value: Any, field: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise TwelveDataAPIError(f"Twelve Data returned an invalid {field} value.") from exc
    if not result.is_finite() or result <= 0:
        raise TwelveDataAPIError(f"Twelve Data returned an invalid {field} value.")
    return result


def _timestamp(value: Any) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise TwelveDataAPIError("Twelve Data returned a candle without a timestamp.")
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise TwelveDataAPIError("Twelve Data returned an invalid candle timestamp.") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


class TwelveDataReadOnlyClient:
    """Minimal Twelve Data REST client. API key is read only from server env."""

    def __init__(self, api_key: str | None = None, timeout: float = 15.0) -> None:
        self._api_key = (api_key or os.getenv("TWELVE_DATA_API_KEY", "")).strip()
        if not self._api_key:
            raise TwelveDataConfigurationError(
                "Missing required environment variable: TWELVE_DATA_API_KEY"
            )
        self._timeout = timeout

    async def _get_json(self, endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
        request_params = {**params, "apikey": self._api_key}
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout, follow_redirects=False
            ) as client:
                response = await client.get(f"{BASE_URL}/{endpoint}", params=request_params)
        except httpx.TimeoutException as exc:
            raise TwelveDataAPIError("Twelve Data request timed out.") from exc
        except httpx.HTTPError as exc:
            raise TwelveDataAPIError("Twelve Data request failed.") from exc

        if response.is_redirect:
            raise TwelveDataAPIError("Twelve Data returned a redirect; request was not followed.")
        if response.status_code == 429:
            raise TwelveDataAPIError("Twelve Data rate limit reached (HTTP 429).")
        if response.status_code >= 400:
            raise TwelveDataAPIError(f"Twelve Data returned HTTP {response.status_code}.")
        try:
            payload = response.json()
        except ValueError as exc:
            raise TwelveDataAPIError("Twelve Data returned a non-JSON response.") from exc
        if not isinstance(payload, dict):
            raise TwelveDataAPIError("Twelve Data returned an unexpected response format.")
        if payload.get("status") == "error" or payload.get("code") is not None:
            # Never echo provider messages: they may include request details.
            code = payload.get("code")
            safe_code = str(code)[:16] if isinstance(code, (str, int)) else "unknown"
            raise TwelveDataAPIError(f"Twelve Data rejected the request (provider code {safe_code}).")
        return payload

    @staticmethod
    def validate_symbol(symbol: str) -> str:
        normalized = symbol.strip().upper()
        if normalized not in SYMBOLS:
            raise TwelveDataConfigurationError(
                "Only XAU/USD, EUR/USD and GBP/USD are enabled for this provider check."
            )
        return normalized

    @staticmethod
    def validate_interval(interval: str) -> str:
        normalized = interval.strip().lower()
        if normalized not in INTERVALS:
            raise TwelveDataConfigurationError("Interval must be 15min or 1h.")
        return normalized

    async def get_quote(self, symbol: str) -> dict[str, Any]:
        symbol = self.validate_symbol(symbol)
        payload = await self._get_json("quote", {"symbol": symbol})
        price_value = payload.get("price") or payload.get("close")
        price = _decimal(price_value, "quote price")
        bid = _decimal((payload.get("bid") or price), "bid")
        ask = _decimal((payload.get("ask") or price), "ask")
        if ask < bid:
            raise TwelveDataAPIError("Twelve Data returned a crossed quote.")
        raw_time = payload.get("timestamp") or payload.get("datetime")
        observed_at = None
        if isinstance(raw_time, (int, float)):
            observed_at = datetime.fromtimestamp(raw_time, tz=timezone.utc)
        elif isinstance(raw_time, str):
            try:
                observed_at = _timestamp(raw_time)
            except TwelveDataAPIError:
                observed_at = None
        return {
            "symbol": symbol,
            "bid": float(bid),
            "ask": float(ask),
            "last": float((bid + ask) / Decimal("2")),
            "timestamp": observed_at.isoformat() if observed_at else None,
            "provider": "twelve_data",
            "read_only": True,
            "execution_enabled": False,
        }

    async def get_candles(
        self, symbol: str, interval: str = "15min", outputsize: int = 120
    ) -> list[dict[str, Any]]:
        symbol = self.validate_symbol(symbol)
        interval = self.validate_interval(interval)
        if not 1 <= outputsize <= 500:
            raise TwelveDataConfigurationError("outputsize must be between 1 and 500.")
        payload = await self._get_json(
            "time_series",
            {
                "symbol": symbol,
                "interval": interval,
                "outputsize": outputsize,
                "timezone": "UTC",
                "order": "ASC",
                "format": "JSON",
            },
        )
        values = payload.get("values")
        if not isinstance(values, list):
            raise TwelveDataAPIError("Twelve Data response did not contain candle values.")
        candles: list[dict[str, Any]] = []
        for item in values:
            if not isinstance(item, dict):
                continue
            try:
                opened = _decimal(item.get("open"), "open")
                high = _decimal(item.get("high"), "high")
                low = _decimal(item.get("low"), "low")
                close = _decimal(item.get("close"), "close")
                if high < max(opened, close, low) or low > min(opened, close, high):
                    continue
                volume_raw = item.get("volume")
                volume = Decimal(str(volume_raw)) if volume_raw not in (None, "") else Decimal("0")
                if not volume.is_finite() or volume < 0:
                    continue
                timestamp = _timestamp(item.get("datetime"))
            except (TwelveDataAPIError, InvalidOperation, TypeError, ValueError):
                continue
            candles.append({
                "timestamp": int(timestamp.timestamp()),
                "datetime": timestamp.isoformat(),
                "open": float(opened),
                "high": float(high),
                "low": float(low),
                "close": float(close),
                "vwap": float((high + low + close) / Decimal("3")),
                "volume": float(volume),
            })
        candles.sort(key=lambda candle: candle["timestamp"])
        if not candles:
            raise TwelveDataAPIError("Twelve Data returned no valid candles.")
        return candles
