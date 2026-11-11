"""Performance reporting for confirmed closes and persisted paper exit fills."""
from decimal import Decimal, InvalidOperation
from typing import Any


class PerformanceAgent:
    name = "performance"

    def summarize(self, closed_trades: list[dict]) -> dict[str, Any]:
        pnls = []
        for item in closed_trades:
            is_confirmed_live_close = (
                item.get("status") == "closed"
                and item.get("exchange_confirmed") is True
                and item.get("realized_pnl") is not None
            )
            is_paper_exit = (
                item.get("status") == "filled"
                and item.get("execution_mode") == "paper"
                and item.get("side") == "SELL"
                and item.get("realized_pnl_usd") is not None
            )
            if not (is_confirmed_live_close or is_paper_exit):
                continue
            raw = item.get("realized_pnl") if is_confirmed_live_close else item.get("realized_pnl_usd")
            try:
                value = Decimal(str(raw))
            except (InvalidOperation, TypeError, ValueError):
                continue
            if value.is_finite():
                pnls.append(float(value))

        if not pnls:
            return {
                "agent": self.name,
                "sample_size": 0,
                "realized_pnl": None,
                "win_rate_pct": None,
                "status": "insufficient_closed_history",
            }
        wins = sum(1 for pnl in pnls if pnl > 0)
        return {
            "agent": self.name,
            "sample_size": len(pnls),
            "realized_pnl": round(sum(pnls), 8),
            "win_rate_pct": round(wins / len(pnls) * 100, 2),
            "average_pnl": round(sum(pnls) / len(pnls), 8),
            "status": "computed_from_paper_and_confirmed_closed_trades",
        }
