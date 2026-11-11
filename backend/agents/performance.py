"""Deterministic performance reporting from persisted, exchange-confirmed closed trades."""
from typing import Any


class PerformanceAgent:
    name = "performance"

    def summarize(self, closed_trades: list[dict]) -> dict[str, Any]:
        # Ignore anything that is not explicitly exchange-confirmed and closed.
        trades = [
            item for item in closed_trades
            if item.get("status") == "closed"
            and item.get("exchange_confirmed") is True
            and isinstance(item.get("realized_pnl"), (int, float))
        ]
        if not trades:
            return {"agent": self.name, "sample_size": 0, "realized_pnl": None, "win_rate_pct": None, "status": "insufficient_confirmed_history"}
        pnls = [float(item["realized_pnl"]) for item in trades]
        wins = sum(1 for pnl in pnls if pnl > 0)
        return {
            "agent": self.name,
            "sample_size": len(pnls),
            "realized_pnl": round(sum(pnls), 8),
            "win_rate_pct": round(wins / len(pnls) * 100, 2),
            "average_pnl": round(sum(pnls) / len(pnls), 8),
            "status": "computed_from_exchange_confirmed_closed_trades",
        }
