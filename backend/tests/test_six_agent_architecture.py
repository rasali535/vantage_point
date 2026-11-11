import unittest
from decimal import Decimal
from unittest.mock import patch

from agents.contracts import PortfolioRiskSnapshot, StrategyProposal, TradeAction
from agents.execution import ExecutionAgent
from agents.performance import PerformanceAgent
from agents.technical_analyst import TechnicalAnalystAgent
from agents.whipsaw_protection import WhipsawProtectionEngine
from risk.engine import DeterministicRiskEngine, RiskPolicy


class SixAgentArchitectureTests(unittest.TestCase):
    def test_technical_analyst_holds_with_insufficient_candles(self):
        report = TechnicalAnalystAgent().analyse([])
        self.assertEqual(report.signal, TradeAction.HOLD)
        self.assertEqual(report.trend, "insufficient_data")

    def test_technical_analyst_calculates_indicators_from_candles(self):
        candles = []
        for i in range(40):
            close = 100 + i * 0.5
            candles.append({"open": close, "high": close + 1, "low": close - 1, "close": close})
        report = TechnicalAnalystAgent().analyse(candles)
        self.assertIsNotNone(report.ema_fast)
        self.assertIsNotNone(report.ema_slow)
        self.assertIsNotNone(report.rsi_14)
        self.assertEqual(report.trend, "uptrend")

    def test_execution_agent_never_enables_execution(self):
        policy = RiskPolicy(
            max_trade_risk_pct=Decimal("0.5"),
            max_daily_loss_pct=Decimal("2"),
            max_drawdown_pct=Decimal("5"),
            max_open_positions=5,
            max_leverage=Decimal("1"),
            require_stop_loss=True,
        )
        agent = ExecutionAgent(DeterministicRiskEngine(policy))
        proposal = StrategyProposal(action=TradeAction.BUY, rationale="test", confidence=0.8)
        result = agent.assess("BTC/USD", proposal, Decimal("50000"), PortfolioRiskSnapshot(equity=Decimal("10000")))
        self.assertEqual(result.status, "sizing_required")
        self.assertFalse(result.execution_enabled)
        self.assertFalse(result.approved_for_review)

    def test_execution_agent_rejects_missing_risk_policy(self):
        with patch.dict("os.environ", {}, clear=True):
            agent = ExecutionAgent(DeterministicRiskEngine(None))
            proposal = StrategyProposal(action=TradeAction.BUY, rationale="test", confidence=0.8)
            result = agent.assess("BTC/USD", proposal, Decimal("50000"), PortfolioRiskSnapshot())
        self.assertEqual(result.status, "risk_policy_not_configured")
        self.assertFalse(result.execution_enabled)

    def test_execution_agent_blocks_when_daily_loss_limit_is_reached(self):
        policy = RiskPolicy(
            max_trade_risk_pct=Decimal("0.5"),
            max_daily_loss_pct=Decimal("2"),
            max_drawdown_pct=Decimal("5"),
            max_open_positions=5,
            max_leverage=Decimal("1"),
            require_stop_loss=True,
        )
        agent = ExecutionAgent(DeterministicRiskEngine(policy))
        proposal = StrategyProposal(action=TradeAction.BUY, rationale="test", confidence=0.8)
        portfolio = PortfolioRiskSnapshot(equity=Decimal("10000"), daily_loss_pct=Decimal("2"))
        result = agent.assess("BTC/USD", proposal, Decimal("50000"), portfolio)
        self.assertEqual(result.status, "rejected")
        self.assertIn("Daily loss limit has been reached.", result.reasons)
        self.assertFalse(result.execution_enabled)

    def test_performance_ignores_unconfirmed_or_open_trades(self):
        result = PerformanceAgent().summarize([
            {"status": "closed", "exchange_confirmed": True, "realized_pnl": 12.5},
            {"status": "closed", "exchange_confirmed": False, "realized_pnl": 1000},
            {"status": "open", "exchange_confirmed": True, "realized_pnl": 999},
        ])
        self.assertEqual(result["sample_size"], 1)
        self.assertEqual(result["realized_pnl"], 12.5)

    def test_performance_reports_insufficient_history_without_fabrication(self):
        result = PerformanceAgent().summarize([])
        self.assertIsNone(result["realized_pnl"])
        self.assertEqual(result["status"], "insufficient_closed_history")

    def test_whipsaw_filter_fails_closed_without_market_data(self):
        result = WhipsawProtectionEngine().evaluate_signal_quality([], [], "BUY")
        self.assertEqual(result["action_recommendation"], "FORCE_HOLD")
        self.assertEqual(result["whipsaw_risk"], "HIGH")


if __name__ == "__main__":
    unittest.main()
