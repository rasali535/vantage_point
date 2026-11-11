"""Execution gate: assess proposals, never submit exchange orders in this phase."""
from decimal import Decimal
from agents.contracts import ExecutionAssessment, PortfolioRiskSnapshot, StrategyProposal
from risk.engine import DeterministicRiskEngine, OrderProposal, RiskPolicy


class ExecutionAgent:
    name = "execution"

    def __init__(self, risk_engine: DeterministicRiskEngine | None = None):
        self.risk_engine = risk_engine or DeterministicRiskEngine()

    def assess(
        self,
        pair: str,
        proposal: StrategyProposal,
        entry_price: Decimal,
        portfolio: PortfolioRiskSnapshot,
        quantity: Decimal | None = None,
        stop_loss: Decimal | None = None,
    ) -> ExecutionAssessment:
        if proposal.action.value == "HOLD":
            return ExecutionAssessment(status="hold", reasons=["Strategy proposal is HOLD."])

        policy = self.risk_engine.policy or RiskPolicy.from_env()
        if policy is None:
            return ExecutionAssessment(
                status="risk_policy_not_configured",
                reasons=["Risk limits are missing or invalid; every proposal is rejected."],
            )

        portfolio_check = self.risk_engine.evaluate_portfolio_state(
            daily_loss_pct=portfolio.daily_loss_pct,
            drawdown_pct=portfolio.drawdown_pct,
            open_positions=portfolio.open_positions,
            leverage=portfolio.leverage,
        )
        if not portfolio_check.get("approved"):
            return ExecutionAssessment(
                status=portfolio_check.get("status", "rejected"),
                reasons=portfolio_check.get("reasons", []),
            )

        if quantity is None or quantity <= 0:
            return ExecutionAssessment(
                status="sizing_required",
                reasons=["Portfolio is within configured limits; validated order quantity and stop-loss are required next."],
                risk_metrics={"portfolio_status": portfolio_check.get("status")},
            )

        risk = self.risk_engine.evaluate(OrderProposal(
            pair=pair,
            side=proposal.action.value,
            quantity=quantity,
            entry_price=entry_price,
            equity=portfolio.equity,
            stop_loss_price=stop_loss,
            daily_loss_pct=portfolio.daily_loss_pct,
            drawdown_pct=portfolio.drawdown_pct,
            open_positions=portfolio.open_positions,
            leverage=portfolio.leverage,
        ))
        return ExecutionAssessment(
            approved_for_review=bool(risk.get("approved")),
            execution_enabled=False,
            status="approved_for_human_review" if risk.get("approved") else "rejected",
            reasons=risk.get("reasons", []) + ["Human approval and a separately enabled execution service are still required."],
            risk_metrics=risk.get("metrics", {}),
        )
