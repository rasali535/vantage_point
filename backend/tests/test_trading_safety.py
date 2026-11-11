import os
import unittest
from unittest.mock import patch

from fastapi import HTTPException

import database
from agents.kraken import KrakenAgent
from agents.featherless import FeatherlessAgent
from agents.transcription import SpeechmaticsAgent
from decimal import Decimal
from risk.engine import DeterministicRiskEngine, OrderProposal, RiskPolicy
from routes.trading import manual_trade


class TradingSafetyTests(unittest.IsolatedAsyncioTestCase):
    async def test_database_missing_uri_fails_closed(self):
        with patch.object(database, "MONGODB_URL", None), patch.object(database, "_client", None), patch.object(database, "_database", None):
            with self.assertRaises(HTTPException) as raised:
                await database.get_database()
        self.assertEqual(raised.exception.status_code, 503)

    async def test_private_account_reads_are_disabled_by_default(self):
        with patch.dict(os.environ, {"KRAKEN_ACCOUNT_READS_ENABLED": "false"}):
            agent = KrakenAgent()
            with self.assertRaisesRegex(RuntimeError, "disabled"):
                await agent.get_balance()

    async def test_order_placement_is_disabled(self):
        agent = KrakenAgent()
        with self.assertRaisesRegex(RuntimeError, "Order placement is disabled"):
            await agent.execute_trade("BTC/USD", "buy", 0.001)

    async def test_manual_trade_endpoint_is_locked(self):
        with self.assertRaises(HTTPException) as raised:
            await manual_trade(None)
        self.assertEqual(raised.exception.status_code, 423)

    async def test_ai_provider_does_not_return_synthetic_analysis(self):
        with patch.dict(os.environ, {"FEATHERLESS_API_KEY": ""}):
            agent = FeatherlessAgent()
            with self.assertRaisesRegex(RuntimeError, "not configured"):
                await agent.chat("meta-llama/test", "system", "user")

    async def test_transcription_does_not_return_mock_text(self):
        with patch.dict(os.environ, {"SPEECHMATICS_API_KEY": ""}):
            agent = SpeechmaticsAgent()
            with self.assertRaisesRegex(RuntimeError, "not configured"):
                await agent.transcribe("/tmp/nonexistent-audio.wav")

    def test_risk_engine_rejects_when_policy_is_missing(self):
        proposal = OrderProposal(
            pair="BTC/USD", side="BUY", quantity=Decimal("0.1"),
            entry_price=Decimal("50000"), equity=Decimal("10000"),
            stop_loss_price=Decimal("49500"), daily_loss_pct=Decimal("0"),
            drawdown_pct=Decimal("0"), open_positions=0,
        )
        decision = DeterministicRiskEngine(policy=None).evaluate(proposal)
        self.assertFalse(decision["approved"])
        self.assertEqual(decision["status"], "risk_policy_not_configured")

    def test_risk_engine_approves_within_explicit_policy(self):
        policy = RiskPolicy(
            max_trade_risk_pct=Decimal("0.5"),
            max_daily_loss_pct=Decimal("2"),
            max_drawdown_pct=Decimal("5"),
            max_open_positions=5,
            max_leverage=Decimal("1"),
            require_stop_loss=True,
        )
        proposal = OrderProposal(
            pair="BTC/USD", side="BUY", quantity=Decimal("0.1"),
            entry_price=Decimal("50000"), equity=Decimal("10000"),
            stop_loss_price=Decimal("49500"), daily_loss_pct=Decimal("0.2"),
            drawdown_pct=Decimal("1"), open_positions=0,
        )
        decision = DeterministicRiskEngine(policy=policy).evaluate(proposal)
        self.assertTrue(decision["approved"])
        self.assertFalse(decision["execution_enabled"])

    def test_risk_engine_rejects_daily_loss_limit_breach(self):
        policy = RiskPolicy(
            max_trade_risk_pct=Decimal("0.5"),
            max_daily_loss_pct=Decimal("2"),
            max_drawdown_pct=Decimal("5"),
            max_open_positions=5,
            max_leverage=Decimal("1"),
            require_stop_loss=True,
        )
        proposal = OrderProposal(
            pair="BTC/USD", side="BUY", quantity=Decimal("0.1"),
            entry_price=Decimal("50000"), equity=Decimal("10000"),
            stop_loss_price=Decimal("49500"), daily_loss_pct=Decimal("2"),
            drawdown_pct=Decimal("1"), open_positions=0,
        )
        decision = DeterministicRiskEngine(policy=policy).evaluate(proposal)
        self.assertFalse(decision["approved"])
        self.assertIn("Daily loss limit has been reached.", decision["reasons"])


if __name__ == "__main__":
    unittest.main()
