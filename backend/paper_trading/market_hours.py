"""Fail-closed market-session and data-freshness gate for new paper entries.

Times are UTC. Weekly session boundaries are deliberately conservative for the
initial Exness FX/metals universe. Broker holiday/early-close windows can be
supplied as PAPER_MARKET_CLOSED_WINDOWS_UTC JSON.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, time, timezone, timedelta
from typing import Any


def _as_utc(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, (int, float)):
        number = float(value)
        if number > 10_000_000_000:
            number /= 1000.0
        try:
            parsed = datetime.fromtimestamp(number, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    elif isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _configured_windows() -> list[dict]:
    raw = os.getenv("PAPER_MARKET_CLOSED_WINDOWS_UTC", "").strip()
    if not raw:
        return []
    try:
        items = json.loads(raw)
        if not isinstance(items, list) or len(items) > 100:
            raise ValueError
        windows = []
        for item in items:
            if not isinstance(item, dict):
                raise ValueError
            start, end = _as_utc(item.get("start")), _as_utc(item.get("end"))
            pairs = item.get("pairs", ["*"])
            if start is None or end is None or end <= start or not isinstance(pairs, list):
                raise ValueError
            if any(not isinstance(pair, str) for pair in pairs):
                raise ValueError
            windows.append({"start": start, "end": end, "pairs": {p.upper() for p in pairs}})
        return windows
    except (TypeError, ValueError, json.JSONDecodeError):
        raise ValueError("Invalid PAPER_MARKET_CLOSED_WINDOWS_UTC; new entries are blocked.")


def _fresh_timestamp(value: Any, now: datetime, max_age_seconds: int, label: str) -> str | None:
    observed = _as_utc(value)
    if observed is None:
        return f"{label} timestamp is missing or invalid."
    age = (now - observed).total_seconds()
    if age < -30:
        return f"{label} timestamp is unexpectedly in the future."
    if age > max_age_seconds:
        return f"{label} is stale ({int(age)}s old; maximum {max_age_seconds}s)."
    return None


def market_entry_block_reason(
    pair: str,
    ticker: dict,
    candles_15m: list[dict],
    candles_1h: list[dict],
    *,
    now: datetime | None = None,
) -> str | None:
    """Return a reason to block a new entry, or None when session/data gates pass."""
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    now = now.astimezone(timezone.utc)
    pair = pair.strip().upper()
    try:
        buffer_minutes = int(os.getenv("PAPER_ENTRY_CLOSE_BUFFER_MINUTES", "60"))
        if not 0 <= buffer_minutes <= 360:
            raise ValueError
        windows = _configured_windows()
    except (TypeError, ValueError):
        return "Market-hours configuration is invalid; new entries fail closed."

    for window in windows:
        if ( "*" in window["pairs"] or pair in window["pairs"] ) and window["start"] <= now < window["end"]:
            return "Broker holiday/early-close blackout window is active."

    metal = pair in {"XAU/USD", "XAG/USD", "XPT/USD", "XPD/USD"}
    # Exness trading server schedule is UTC. Use the earlier conservative close
    # for metals because holiday schedules can shorten their Friday session.
    friday_close = time(19, 45) if metal else time(21, 0)
    friday_cutoff = (datetime.combine(now.date(), friday_close, tzinfo=timezone.utc)
                     - timedelta(minutes=buffer_minutes))
    if now.weekday() == 4 and now >= friday_cutoff:
        return f"Friday entry cutoff reached ({buffer_minutes}m before the conservative {friday_close.strftime('%H:%M')} UTC close)."
    if now.weekday() == 5:
        return "Weekend market closure; new entries are blocked."
    if now.weekday() == 6:
        reopen = time(23, 5) if metal else time(21, 5)
        if now.time() < reopen:
            return f"Sunday session has not reopened (conservative reopen {reopen.strftime('%H:%M')} UTC)."

    reason = _fresh_timestamp(ticker.get("timestamp"), now, 120, "Live quote")
    if reason:
        return reason
    if not candles_15m or not candles_1h:
        return "15m/1h candle history is missing."
    reason = _fresh_timestamp(candles_15m[-1].get("timestamp"), now, 30 * 60, "Latest M15 candle")
    if reason:
        return reason
    reason = _fresh_timestamp(candles_1h[-1].get("timestamp"), now, 90 * 60, "Latest H1 candle")
    if reason:
        return reason
    return None
