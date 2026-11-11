"""Execution gate: assess proposals, never submit exchange orders in this phase."""
from decimal import Decimal
from agents.contracts import ExecutionAssessment, PortfolioRiskSnapshot, StrategyProposal
from risk.engine import DeterministicRiskEngine, OrderProposal


class ExecutionAgent:
    name = "execution"

    def __init__(self, risk_engine: DeterministicRiskEngine | None = None):
        self.risk_engine = risk_engine or DeterministicRiskEngine()

    def assess(self, pair: str, proposal: StrategyProposal, entry_price: Decimal, stop_loss: Decimal | None, portfolio: PortfolioRiskSnapshot) -> ExecutionAssessment:
        if proposal.action.value == "HOLD":
            return ExecutionAssessment(status="hold", reasons=["Strategy proposal is HOLD."])
        risk = self.risk_engine.evaluate(OrderProposal(
            pair=pair, side=proposal.action.value, quantity=Decimal("0"),
            entry_price=entry_price, equity=portfolio.equity, stop_loss_price=stop_loss,
            daily_loss_pct=portfolio.daily_loss_pct, drawdown_pct=portfolio.drawdown_pct,
            open_positions=portfolio.open_positions, leverage=portfolio.leverage,
        ))
        # Quantity is intentionally unavailable in the advisory stage, so the
        # gate cannot approve a live order. Sizing must be a separately reviewed step.
        return ExecutionAssessment(
            approved_for_review=False,
            execution_enabled=False,
            status="sizing_required" if risk.get("status") != "risk_policy_not_configured" else "risk_policy_not_configured",
            reasons=risk.get("reasons", []) + ["Order quantity and human approval are required; exchange submission is disabled."],
            risk_metrics=risk.get("metrics", {}),
        )
