"""Deterministic advisory risk summary; the risk engine remains authoritative."""
import math
from agents.contracts import AgentFinding


def _number(value):
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


class RiskManagerAgent:
    name = "risk_manager"

    async def assess(self, pair: str, ticker: dict, technical: dict, portfolio: dict) -> AgentFinding:
        warnings = []
        evidence = []
        last = _number((ticker or {}).get("last"))
        atr = _number((technical or {}).get("atr"))
        daily_loss = _number((portfolio or {}).get("daily_loss_pct"))
        drawdown = _number((portfolio or {}).get("drawdown_pct"))
        open_positions = _number((portfolio or {}).get("open_positions"))

        if last is None or last <= 0:
            warnings.append("Ticker price is unavailable; no trade should be proposed.")
        if atr is None or atr <= 0:
            warnings.append("ATR is unavailable; stop distance cannot be validated.")
        elif last and last > 0:
            atr_pct = atr / last * 100
            evidence.append(f"ATR represents {atr_pct:.3f}% of the latest price.")
            if atr_pct >= 3:
                warnings.append("Volatility is elevated relative to price.")
        if daily_loss is not None:
            evidence.append(f"Current daily loss: {daily_loss:.3f}%.")
        if drawdown is not None:
            evidence.append(f"Current portfolio drawdown: {drawdown:.3f}%.")
        if open_positions is not None:
            evidence.append(f"Open positions: {int(open_positions)}.")
        if not evidence:
            warnings.append("Portfolio risk context is incomplete.")

        return AgentFinding(
            agent=self.name,
            summary=f"Deterministic advisory risk review for {pair}; execution limits are enforced separately.",
            evidence=evidence,
            confidence=0.8 if not warnings else 0.55,
            warnings=warnings,
        )
