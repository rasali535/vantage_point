"""Deterministic strategy proposal based on verified technical and risk findings."""
from agents.contracts import StrategyProposal, TradeAction


class StrategyAgent:
    name = "strategy"

    async def propose(self, market: dict, technical: dict, risk: dict, performance: dict | None = None) -> StrategyProposal:
        raw_signal = (technical or {}).get("signal", "HOLD")
        signal = raw_signal.value if isinstance(raw_signal, TradeAction) else str(raw_signal).upper()
        warnings = list((market or {}).get("warnings") or []) + list((risk or {}).get("warnings") or [])
        trend = str((technical or {}).get("trend") or "unknown")
        rsi = (technical or {}).get("rsi_14")
        atr = (technical or {}).get("atr")
        evidence = list((technical or {}).get("evidence") or [])
        invalidation = ["A change in the technical signal", "A deterministic risk-policy rejection"]

        if signal not in {"BUY", "SELL"}:
            return StrategyProposal(
                action=TradeAction.HOLD,
                rationale=f"Deterministic strategy returned HOLD: technical signal is {signal}.",
                confidence=0.35,
                invalidation_conditions=invalidation,
            )
        if not atr or float(atr) <= 0 or warnings:
            return StrategyProposal(
                action=TradeAction.HOLD,
                rationale="Deterministic strategy returned HOLD because market/risk inputs are incomplete or carry warnings: " + "; ".join(warnings[:3]),
                confidence=0.3,
                invalidation_conditions=invalidation,
            )

        confidence = 0.62
        if trend in {"uptrend", "downtrend"}:
            confidence += 0.08
        if rsi is not None:
            rsi_value = float(rsi)
            if (signal == "BUY" and 40 <= rsi_value <= 68) or (signal == "SELL" and 32 <= rsi_value <= 60):
                confidence += 0.06
        confidence = min(0.82, confidence)
        return StrategyProposal(
            action=TradeAction(signal),
            rationale=f"Deterministic {signal} proposal from {trend} technical conditions. " + (" ".join(evidence[:3])),
            confidence=confidence,
            invalidation_conditions=invalidation,
        )
