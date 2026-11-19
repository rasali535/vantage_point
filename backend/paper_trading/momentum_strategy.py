"""Momentum strategy rules for medium-duration paper positions.

This module is intentionally pure: it proposes signals from candle series and does
not place orders, modify account state, or bypass portfolio risk controls.
"""
from __future__ import annotations

from dataclasses import dataclass
from agents.contracts import TradeAction


@dataclass(frozen=True)
class MomentumSignal:
    action: TradeAction
    confidence: float
    rationale: str
    atr: float | None
    stop_distance: float | None
    target_distance: float | None


def _ema(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    alpha = 2.0 / (period + 1.0)
    result = sum(values[:period]) / period
    for value in values[period:]:
        result = alpha * value + (1.0 - alpha) * result
    return result


def _atr(candles: list[dict], period: int = 14) -> float | None:
    if len(candles) < period + 1:
        return None
    ranges = []
    for i in range(len(candles) - period, len(candles)):
        high = float(candles[i]["high"])
        low = float(candles[i]["low"])
        previous_close = float(candles[i - 1]["close"])
        ranges.append(max(high - low, abs(high - previous_close), abs(low - previous_close)))
    return sum(ranges) / len(ranges)


def _valid(candles: list[dict]) -> bool:
    try:
        for candle in candles:
            values = [float(candle[key]) for key in ("open", "high", "low", "close")]
            if any(not __import__("math").isfinite(v) or v <= 0 for v in values):
                return False
            if values[1] < values[2]:
                return False
        return True
    except (KeyError, TypeError, ValueError):
        return False


def evaluate_momentum(candles_15m: list[dict], candles_1h: list[dict]) -> MomentumSignal:
    """Buy only when 15m momentum and 1h trend align; otherwise HOLD.

    Uses EMA 20/50 on each timeframe, a 14-period ATR stop (1.5x), and
    a fixed 2R target. This is long-only until a short-selling simulator exists.
    """
    hold = MomentumSignal(TradeAction.HOLD, 0.0, "Insufficient or invalid candle data; no entry.", None, None, None)
    if not _valid(candles_15m) or not _valid(candles_1h):
        return hold
    c15 = [float(c["close"]) for c in candles_15m]
    c60 = [float(c["close"]) for c in candles_1h]
    if len(c15) < 50 or len(c60) < 50:
        return hold
    ema20_15, ema50_15 = _ema(c15, 20), _ema(c15, 50)
    ema20_60, ema50_60 = _ema(c60, 20), _ema(c60, 50)
    atr = _atr(candles_15m)
    if not all(v is not None for v in (ema20_15, ema50_15, ema20_60, ema50_60, atr)) or atr <= 0:
        return hold
    price = c15[-1]
    bullish = ema20_15 > ema50_15 and ema20_60 > ema50_60 and price > ema20_15
    bearish = ema20_15 < ema50_15 and ema20_60 < ema50_60 and price < ema20_15
    if bullish:
        stop_distance = atr * 1.5
        target_distance = stop_distance * 2.0
        confidence = min(0.90, 0.65 + min(0.20, (ema20_15 - ema50_15) / price * 100))
        return MomentumSignal(
            TradeAction.BUY, round(confidence, 2),
            "15m EMA20/50 bullish and price above EMA20; 1h EMA20/50 trend aligned. ATR-based 1.5R stop with 2R target.",
            atr, stop_distance, target_distance,
        )
    reason = "Bearish trend alignment; long-only system waits." if bearish else "Timeframes are not aligned; avoid sideways/choppy entries."
    return MomentumSignal(TradeAction.HOLD, 0.0, reason, atr, None, None)
