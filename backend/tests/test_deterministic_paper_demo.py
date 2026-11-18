import os
import unittest
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from agents.contracts import AgentFinding, PortfolioRiskSnapshot, TechnicalReport, TradeAction
from agents.market_intelligence import MarketIntelligenceAgent
from agents.risk_manager import RiskManagerAgent
from agents.strategy import StrategyAgent
from paper_trading.engine import initial_account
from paper_trading.autopilot import _execute_signal
from risk.engine import RiskPolicy


class DeterministicAgentTests(unittest.IsolatedAsyncioTestCase):
    async def test_market_intelligence_uses_supplied_candles_only(self):
        candles = [
            {"close": 100 + i, "high": 101 + i, "low": 99 + i}
            for i in range(20)
        ]
        finding = await MarketIntelligenceAgent().analyse(
            "BTC/USD",
            {"last": 119, "bid": 118.9, "ask": 119.1, "change_percent": 2.0},
            candles,
        )
        self.assertEqual(finding.agent, "market_intelligence")
        self.assertTrue(finding.evidence)
        self.assertFalse(finding.warnings)

    async def test_risk_manager_is_advisory_and_reports_atr(self):
        finding = await RiskManagerAgent().assess(
            "BTC/USD",
            {"last": 100},
            {"atr": 1.5},
            {"daily_loss_pct": 0, "drawdown_pct": 0, "open_positions": 0},
        )
        self.assertEqual(finding.agent, "risk_manager")
        self.assertTrue(any("ATR" in item for item in finding.evidence))

    async def test_strategy_holds_when_risk_or_market_inputs_have_warnings(self):
        proposal = await StrategyAgent().propose(
            {"warnings": []},
            {"signal": "BUY", "trend": "uptrend", "atr": 1, "rsi_14": 55},
            {"warnings": ["Volatility is elevated."]},
        )
        self.assertEqual(proposal.action, TradeAction.HOLD)

    async def test_strategy_uses_deterministic_technical_signal(self):
        proposal = await StrategyAgent().propose(
            {"warnings": [], "evidence": ["Momentum positive"]},
            {"signal": "BUY", "trend": "uptrend", "atr": 1, "rsi_14": 55, "evidence": ["EMA fast above slow"]},
            {"warnings": []},
        )
        self.assertEqual(proposal.action, TradeAction.BUY)
        self.assertGreaterEqual(proposal.confidence, 0.6)


class PaperAutopilotSizingRegressionTests(unittest.IsolatedAsyncioTestCase):
    async def test_buy_signal_builds_stop_and_target_and_records_paper_fill(self):
        from paper_trading import autopilot

        candles = [
            {"open": 100 + i * 0.1, "close": 100.05 + i * 0.1,
             "high": 100.2 + i * 0.1, "low": 99.9 + i * 0.1}
            for i in range(40)
        ]
        report = TechnicalReport(
            trend="uptrend", rsi_14=55, ema_fast=104, ema_slow=103,
            atr=0.5, signal=TradeAction.BUY, evidence=["EMA bullish"],
        )
        scalp = {
            "signal": TradeAction.BUY,
            "confidence": Decimal("0.82"),
            "timeframe": "1m+5m",
            "tech_5m": report,
            "tech_1m": report,
            "atr": 0.5,
            "vel_1m": 0.5,
            "vel_5m": 0.5,
            "rationale": "Test bullish setup",
        }
        account = initial_account("100.00")
        portfolio = PortfolioRiskSnapshot(
            equity=Decimal("100"), daily_loss_pct=Decimal("0"),
            drawdown_pct=Decimal("0"), open_positions=0, leverage=Decimal("1"),
        )
        policy = RiskPolicy(
            max_trade_risk_pct=Decimal("2"),
            max_daily_loss_pct=Decimal("6"),
            max_drawdown_pct=Decimal("12"),
            max_open_positions=6,
            max_leverage=Decimal("1"),
            require_stop_loss=True,
        )

        async def save_account(_db, _before, after):
            return after

        with patch.dict(os.environ, {
            "PAPER_AUTOTRADING_USE_LLM": "false",
            "PAPER_AUTOTRADING_MIN_CONFIDENCE": "0.62",
            "PAPER_AUTOTRADING_MAX_POSITION_PCT": "32",
        }), patch.object(autopilot, "_evaluate_scalp_signal", return_value=scalp), \
             patch.object(autopilot, "_active_risk_policy", return_value=policy), \
             patch.object(autopilot, "_save_account", new=AsyncMock(side_effect=save_account)), \
             patch.object(autopilot, "_record_event", new=AsyncMock()):
            result = await _execute_signal(
                object(), account, "BTC/USD", {"last": "100"},
                candles, portfolio, {},
            )

        self.assertEqual(result["decision"], "BUY")
        self.assertGreater(Decimal(result["fill"]["take_profit"]), Decimal(result["fill"]["fill_price"]))
        self.assertLess(Decimal(result["fill"]["stop_loss"]), Decimal(result["fill"]["fill_price"]))
        self.assertEqual(result["fill"]["execution_mode"], "paper")
        self.assertFalse(result["fill"]["exchange_order_submitted"])


if __name__ == "__main__":
    unittest.main()
