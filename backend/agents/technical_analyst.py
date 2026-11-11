"""Deterministic technical indicators; no LLM-generated indicator values."""
import math
from agents.contracts import TechnicalReport, TradeAction


def _ema(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    alpha = 2 / (period + 1)
    value = sum(values[:period]) / period
    for sample in values[period:]:
        value = alpha * sample + (1 - alpha) * value
    return value


def _rsi(values: list[float], period: int = 14) -> float | None:
    if len(values) <= period:
        return None
    changes = [values[i] - values[i - 1] for i in range(1, len(values))]
    gains = [max(change, 0.0) for change in changes[-period:]]
    losses = [max(-change, 0.0) for change in changes[-period:]]
    avg_gain, avg_loss = sum(gains) / period, sum(losses) / period
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    return 100 - (100 / (1 + avg_gain / avg_loss))


class TechnicalAnalystAgent:
    name = "technical_analyst"

    def analyse(self, candles: list) -> TechnicalReport:
        try:
            closes = [float(c["close"]) for c in candles]
            highs = [float(c["high"]) for c in candles]
            lows = [float(c["low"]) for c in candles]
            if (
                len(closes) < 30
                or any(not math.isfinite(x) or x <= 0 for x in closes)
                or any(not math.isfinite(x) or x <= 0 for x in highs + lows)
                or any(high < low for high, low in zip(highs, lows))
            ):
                return TechnicalReport(trend="insufficient_data", warnings=["At least 30 valid candles are required; recommendation defaults to HOLD."])
            fast, slow = _ema(closes, 9), _ema(closes, 21)
            rsi = _rsi(closes)
            true_ranges = []
            # Use the latest 14 true ranges; older candles should not determine
            # the stop distance for a current autonomous paper entry.
            for i in range(max(1, len(closes) - 14), len(closes)):
                true_ranges.append(max(
                    highs[i] - lows[i],
                    abs(highs[i] - closes[i - 1]),
                    abs(lows[i] - closes[i - 1]),
                ))
            atr = sum(true_ranges) / len(true_ranges) if true_ranges else None
            signal = TradeAction.HOLD
            trend = "sideways"
            if fast is not None and slow is not None:
                if fast > slow:
                    trend = "uptrend"
                elif fast < slow:
                    trend = "downtrend"
            if trend == "uptrend" and rsi is not None and 45 <= rsi <= 68:
                signal = TradeAction.BUY
            elif trend == "downtrend" and rsi is not None and 32 <= rsi <= 55:
                signal = TradeAction.SELL
            evidence = [f"EMA9={fast:.4f}", f"EMA21={slow:.4f}"] if fast and slow else []
            if rsi is not None:
                evidence.append(f"RSI14={rsi:.2f}")
            return TechnicalReport(trend=trend, rsi_14=rsi, ema_fast=fast, ema_slow=slow, atr=atr, signal=signal, evidence=evidence)
        except (KeyError, TypeError, ValueError, ZeroDivisionError) as exc:
            raise RuntimeError("Technical analysis could not validate the supplied candle series.") from exc
