"""Read-only Exness market-data adapter for Vantage Point paper trading.

This adapter supplies prices and OHLC candles only. It has no order API and
cannot place, modify, or close orders on an Exness account.
"""
from __future__ import annotations

import asyncio
from datetime import datetime
import time
from typing import Any

from markets.providers.exness import ExnessReadOnlyClient


PAIR_TO_INSTRUMENT = {
    "XAU/USD": "XAUUSD",
    "EUR/USD": "EURUSD",
    "GBP/USD": "GBPUSD",
}


class ExnessPaperMarketData:
    """Translate Exness read-only ticks/candles into the paper engine contract."""

    def __init__(self, client: ExnessReadOnlyClient | None = None) -> None:
        # Lazy construction keeps missing credentials from preventing API startup.
        self._client = client
        self._ticks: dict[str, dict[str, Any]] = {}
        # Track freshness per instrument: refreshing EURUSD must not make an
        # older cached XAUUSD/GBPUSD quote appear fresh.
        self._tick_refreshed_at: dict[str, float] = {}
        self._refresh_lock = asyncio.Lock()
        self._candle_cache: dict[tuple[str, str], tuple[float, list[dict[str, Any]]]] = {}
        self._candle_locks: dict[tuple[str, str], asyncio.Lock] = {}

    def _get_client(self) -> ExnessReadOnlyClient:
        if self._client is None:
            self._client = ExnessReadOnlyClient()
        return self._client

    @staticmethod
    def instrument_for_pair(pair: str) -> str:
        normalized = pair.strip().upper()
        instrument = PAIR_TO_INSTRUMENT.get(normalized)
        if not instrument:
            raise ValueError(f"{normalized} is not enabled for the initial Exness paper feed.")
        return instrument

    async def refresh_ticks(self, pairs: list[str]) -> None:
        # The current Exness Trading API rollout supports only the explicitly
        # mapped FX/metals instruments. Ignore unrelated watchlist symbols here;
        # their individual get_ticker calls fail closed with a clear ValueError.
        supported_pairs = [
            pair for pair in pairs if pair.strip().upper() in PAIR_TO_INSTRUMENT
        ]
        instruments = list(dict.fromkeys(
            PAIR_TO_INSTRUMENT[pair.strip().upper()] for pair in supported_pairs
        ))
        if not instruments:
            raise RuntimeError(
                "No Exness-supported instruments are present in the paper watchlist."
            )
        async with self._refresh_lock:
            ticks = await self._get_client().get_ticks(instruments)
            refreshed: dict[str, dict[str, Any]] = {}
            for tick in ticks:
                instrument = tick.get("instrument")
                bid, ask = tick.get("bid"), tick.get("ask")
                if (
                    instrument in instruments
                    and isinstance(bid, (int, float))
                    and isinstance(ask, (int, float))
                    and 0 < bid <= ask
                ):
                    refreshed[instrument] = dict(tick)
            now = time.monotonic()
            self._ticks.update(refreshed)
            for instrument in refreshed:
                self._tick_refreshed_at[instrument] = now
            missing = sorted(set(instruments) - set(refreshed))
            if not refreshed:
                raise RuntimeError(
                    "Exness returned no valid bid/ask ticks for the requested instruments."
                )
            if missing:
                # Partial snapshots are usable for the instruments actually
                # received; missing symbols will be retried independently.
                import logging
                logging.getLogger(__name__).warning(
                    "exness_tick_snapshot_partial received=%s missing=%s",
                    sorted(refreshed), missing,
                )

    async def get_ticker(self, pair: str) -> dict[str, Any]:
        instrument = self.instrument_for_pair(pair)
        if (
            instrument not in self._ticks
            or time.monotonic() - self._tick_refreshed_at.get(instrument, 0.0) > 5.0
        ):
            await self.refresh_ticks([pair])
        tick = self._ticks.get(instrument)
        if not tick:
            raise RuntimeError(f"Exness did not return a usable tick for {instrument}.")
        bid, ask = float(tick["bid"]), float(tick["ask"])
        mid = (bid + ask) / 2.0
        return {
            "pair": pair.strip().upper(),
            "bid": bid,
            "ask": ask,
            "last": mid,
            "high_24h": mid,
            "low_24h": mid,
            "volume_24h": 0.0,
            "open": mid,
            "change_percent": 0.0,
            "timestamp": tick.get("timestamp"),
            "source": "exness_read_only",
        }

    @staticmethod
    def _mid_ohlc(candle: dict[str, Any], field: str) -> float:
        bid = candle.get("bid")
        ask = candle.get("ask")
        if isinstance(bid, dict) and isinstance(ask, dict):
            return (float(bid[field]) + float(ask[field])) / 2.0
        return float(candle[field])

    @classmethod
    def normalize_candle(cls, candle: dict[str, Any]) -> dict[str, Any] | None:
        try:
            opened = cls._mid_ohlc(candle, "open")
            high = cls._mid_ohlc(candle, "high")
            low = cls._mid_ohlc(candle, "low")
            close = cls._mid_ohlc(candle, "close")
            if min(opened, high, low, close) <= 0:
                return None
            raw_time = candle.get("time")
            timestamp = None
            if isinstance(raw_time, str):
                timestamp = int(datetime.fromisoformat(raw_time.replace("Z", "+00:00")).timestamp())
            return {
                "timestamp": timestamp,
                "open": opened,
                "high": max(opened, high, low, close),
                "low": min(opened, high, low, close),
                "close": close,
                "vwap": (high + low + close) / 3.0,
                "volume": float(candle.get("volume") or 0.0),
            }
        except (KeyError, TypeError, ValueError, OverflowError):
            return None

    async def get_ohlc(self, pair: str, interval: int = 5) -> list[dict[str, Any]]:
        instrument = self.instrument_for_pair(pair)
        timeframe = "M1" if interval <= 1 else "M5" if interval <= 5 else "M15" if interval <= 15 else "H1"
        cache_key = (instrument, timeframe)
        cache_ttl = 60.0 if timeframe == "M15" else 180.0 if timeframe == "H1" else 30.0
        cached = self._candle_cache.get(cache_key)
        now = time.monotonic()
        if cached and now - cached[0] < cache_ttl:
            return [dict(item) for item in cached[1]]
        lock = self._candle_locks.setdefault(cache_key, asyncio.Lock())
        async with lock:
            cached = self._candle_cache.get(cache_key)
            now = time.monotonic()
            if cached and now - cached[0] < cache_ttl:
                return [dict(item) for item in cached[1]]
            candles = await self._get_client().get_candles(
                instrument, timeframe=timeframe, count=120, price_type="both"
            )
        parsed = [
            normalized
            for candle in candles
            if isinstance(candle, dict)
            for normalized in [self.normalize_candle(candle)]
            if normalized is not None
        ]
        minimum = 50 if timeframe in {"M15", "H1"} else 30
        if len(parsed) < minimum:
            raise RuntimeError(
                f"Exness returned only {len(parsed)} valid {timeframe} candles for {instrument}; "
                f"at least {minimum} are required for the momentum indicators."
            )
        self._candle_cache[cache_key] = (time.monotonic(), parsed)
        return [dict(item) for item in parsed]
