"""Deterministic, LLM-independent risk gate.

Risk limits are operator-configured. Missing or invalid policy configuration
always rejects a proposal; no suggested defaults are silently applied.
"""
import os
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class RiskPolicy:
    max_trade_risk_pct: Decimal
    max_daily_loss_pct: Decimal
    max_drawdown_pct: Decimal
    max_open_positions: int
    max_leverage: Decimal
    require_stop_loss: bool

    @classmethod
    def from_env(cls) -> Optional["RiskPolicy"]:
        required = (
            "RISK_MAX_TRADE_RISK_PCT",
            "RISK_MAX_DAILY_LOSS_PCT",
            "RISK_MAX_DRAWDOWN_PCT",
            "RISK_MAX_OPEN_POSITIONS",
            "RISK_MAX_LEVERAGE",
            "RISK_REQUIRE_STOP_LOSS",
        )
        if any(not os.getenv(key) for key in required):
            return None

        try:
            stop_loss_setting = os.environ["RISK_REQUIRE_STOP_LOSS"].lower()
            if stop_loss_setting not in {"true", "false"}:
                return None
            policy = cls(
                max_trade_risk_pct=Decimal(os.environ["RISK_MAX_TRADE_RISK_PCT"]),
                max_daily_loss_pct=Decimal(os.environ["RISK_MAX_DAILY_LOSS_PCT"]),
                max_drawdown_pct=Decimal(os.environ["RISK_MAX_DRAWDOWN_PCT"]),
                max_open_positions=int(os.environ["RISK_MAX_OPEN_POSITIONS"]),
                max_leverage=Decimal(os.environ["RISK_MAX_LEVERAGE"]),
                require_stop_loss=stop_loss_setting == "true",
            )
        except (InvalidOperation, ValueError, KeyError):
            return None

        if (
            not policy.max_trade_risk_pct.is_finite()
            or not policy.max_daily_loss_pct.is_finite()
            or not policy.max_drawdown_pct.is_finite()
            or not policy.max_leverage.is_finite()
            or policy.max_trade_risk_pct <= 0
            or policy.max_daily_loss_pct <= 0
            or policy.max_drawdown_pct <= 0
            or policy.max_open_positions < 1
            or policy.max_leverage < 1
        ):
            return None
        return policy


@dataclass(frozen=True)
class OrderProposal:
    pair: str
    side: str
    quantity: Decimal
    entry_price: Decimal
    equity: Decimal
    stop_loss_price: Optional[Decimal]
    daily_loss_pct: Decimal
    drawdown_pct: Decimal
    open_positions: int
    leverage: Decimal = Decimal("1")


class DeterministicRiskEngine:
    def __init__(self, policy: Optional[RiskPolicy] = None):
        self.policy = policy


    def evaluate_portfolio_state(
        self,
        daily_loss_pct: Decimal,
        drawdown_pct: Decimal,
        open_positions: int,
        leverage: Decimal,
    ) -> Dict[str, Any]:
        """Check account-wide limits before a strategy can proceed to sizing."""
        policy = self.policy or RiskPolicy.from_env()
        if policy is None:
            return {
                "approved": False,
                "status": "risk_policy_not_configured",
                "reasons": ["Risk limits are missing or invalid; operator configuration is required."],
            }

        values = (daily_loss_pct, drawdown_pct, leverage)
        if any(not value.is_finite() for value in values):
            return {"approved": False, "status": "rejected", "reasons": ["Portfolio risk values must be finite."]}
        reasons = []
        if daily_loss_pct < 0 or drawdown_pct < 0 or open_positions < 0 or leverage < 1:
            reasons.append("Portfolio risk values are outside valid bounds.")
        if daily_loss_pct >= policy.max_daily_loss_pct:
            reasons.append("Daily loss limit has been reached.")
        if drawdown_pct >= policy.max_drawdown_pct:
            reasons.append("Maximum drawdown limit has been reached.")
        if open_positions >= policy.max_open_positions:
            reasons.append("Maximum open-position count has been reached.")
        if leverage > policy.max_leverage:
            reasons.append("Current leverage exceeds the configured maximum.")
        return {
            "approved": not reasons,
            "status": "portfolio_within_limits" if not reasons else "rejected",
            "reasons": reasons,
            "execution_enabled": False,
        }

    def evaluate(self, proposal: OrderProposal) -> Dict[str, Any]:
        policy = self.policy or RiskPolicy.from_env()
        if policy is None:
            return {
                "approved": False,
                "status": "risk_policy_not_configured",
                "reasons": ["Risk limits are missing or invalid; operator configuration is required."],
            }

        reasons: List[str] = []
        side = proposal.side.upper()

        numeric_values = [
            proposal.quantity, proposal.entry_price, proposal.equity,
            proposal.daily_loss_pct, proposal.drawdown_pct, proposal.leverage,
        ]
        if any(not value.is_finite() for value in numeric_values):
            return {
                "approved": False,
                "status": "rejected",
                "reasons": ["All numeric proposal values must be finite."],
                "execution_enabled": False,
            }
        if side not in {"BUY", "SELL"}:
            reasons.append("Order side must be BUY or SELL.")
        if not proposal.pair.strip():
            reasons.append("Market pair is required.")
        if proposal.quantity <= 0 or proposal.entry_price <= 0 or proposal.equity <= 0:
            reasons.append("Quantity, entry price and account equity must be positive.")
        if proposal.daily_loss_pct < 0 or proposal.drawdown_pct < 0:
            reasons.append("Loss and drawdown percentages cannot be negative.")
        if proposal.open_positions < 0:
            reasons.append("Open position count cannot be negative.")
        if proposal.leverage < 1:
            reasons.append("Leverage must be at least 1x.")

        stop_loss = proposal.stop_loss_price
        if policy.require_stop_loss and stop_loss is None:
            reasons.append("A stop-loss price is required by policy.")
        elif stop_loss is not None:
            if not stop_loss.is_finite():
                return {
                    "approved": False,
                    "status": "rejected",
                    "reasons": ["Stop-loss price must be finite."],
                    "execution_enabled": False,
                }
            elif stop_loss <= 0:
                reasons.append("Stop-loss price must be positive.")
            elif side == "BUY" and stop_loss >= proposal.entry_price:
                reasons.append("A BUY stop-loss must be below the proposed entry price.")
            elif side == "SELL" and stop_loss <= proposal.entry_price:
                reasons.append("A SELL stop-loss must be above the proposed entry price.")

        trade_risk_pct = None
        if (
            proposal.quantity > 0
            and proposal.entry_price > 0
            and proposal.equity > 0
            and stop_loss is not None
            and stop_loss > 0
        ):
            trade_risk_pct = (
                abs(proposal.entry_price - stop_loss) * proposal.quantity
                / proposal.equity * Decimal("100")
            )
            if trade_risk_pct > policy.max_trade_risk_pct:
                reasons.append("Proposed loss at stop exceeds the per-trade risk limit.")

        if proposal.daily_loss_pct >= policy.max_daily_loss_pct:
            reasons.append("Daily loss limit has been reached.")
        if proposal.drawdown_pct >= policy.max_drawdown_pct:
            reasons.append("Maximum drawdown limit has been reached.")
        if proposal.open_positions >= policy.max_open_positions:
            reasons.append("Maximum open-position count has been reached.")
        if proposal.leverage > policy.max_leverage:
            reasons.append("Proposed leverage exceeds the configured maximum.")

        approved = not reasons
        return {
            "approved": approved,
            "status": "approved_for_review" if approved else "rejected",
            "reasons": reasons,
            "metrics": {
                "trade_risk_pct": float(trade_risk_pct) if trade_risk_pct is not None else None,
                "daily_loss_pct": float(proposal.daily_loss_pct),
                "drawdown_pct": float(proposal.drawdown_pct),
                "open_positions": proposal.open_positions,
                "leverage": float(proposal.leverage),
            },
            # Approval by this gate is not permission to submit an order.
            "execution_enabled": False,
        }


risk_engine = DeterministicRiskEngine()
