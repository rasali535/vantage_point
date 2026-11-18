"""Deterministic market context derived only from verified provider data."""
import math
from agents.contracts import AgentFinding


def _finite(value):
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


class MarketIntelligenceAgent:
    name = "market_intelligence"

    async def analyse(self, pair: str, ticker: dict, candles: list) -> AgentFinding:
        valid = [c for c in (candles or []) if isinstance(c, dict)]
        closes = [_finite(c.get("close")) for c in valid]
        closes = [value for value in closes if value is not None and value > 0]
        last = _finite((ticker or {}).get("last"))
        bid = _finite((ticker or {}).get("bid"))
        ask = _finite((ticker or {}).get("ask"))
        change = _finite((ticker or {}).get("change_percent"))
        warnings = []
        evidence = []

        if len(closes) < 2:
            warnings.append("Insufficient valid candle history for momentum analysis.")
        else:
            lookback = closes[-min(12, len(closes))]
            momentum_pct = ((closes[-1] - lookback) / lookback * 100) if lookback else 0.0
            evidence.append(f"Recent candle momentum: {momentum_pct:+.3f}% over {min(12, len(closes)) - 1} intervals.")
            evidence.append(f"Latest close: {closes[-1]:.8g}.")
        if last is not None:
            evidence.append(f"Verified ticker last price: {last:.8g}.")
        else:
            warnings.append("Ticker last price is missing or invalid.")
        if change is not None:
            evidence.append(f"Provider-reported 24-hour change: {change:+.3f}%.")
        if bid is not None and ask is not None and last and last > 0 and ask >= bid:
            spread_pct = (ask - bid) / last * 100
            evidence.append(f"Observed bid/ask spread: {spread_pct:.4f}%.")
            if spread_pct > 0.25:
                warnings.append("Observed spread is elevated; execution costs may be material.")

        confidence = min(0.88, 0.35 + min(len(closes), 30) / 60)
        if len(closes) < 12 or last is None:
            confidence = min(confidence, 0.35)
        summary = (
            f"{pair} market context calculated from {len(closes)} valid closes"
            + (f"; latest close {closes[-1]:.8g}." if closes else "; candle history unavailable.")
        )
        return AgentFinding(
            agent=self.name,
            summary=summary,
            evidence=evidence,
            confidence=confidence,
            warnings=warnings,
        )
