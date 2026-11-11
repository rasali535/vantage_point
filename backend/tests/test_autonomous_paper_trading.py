import os
import unittest
from decimal import Decimal
from unittest.mock import patch

from paper_trading.autopilot import calculate_spot_quantity, configured_pairs
from paper_trading.engine import PaperTradeError
from agents.performance import PerformanceAgent


class AutonomousPaperSizingTests(unittest.TestCase):
    def test_size_uses_trade_risk_budget(self):
        quantity = calculate_spot_quantity(
            equity=Decimal("1000"),
            cash=Decimal("1000"),
            entry_estimate=Decimal("100"),
            stop_price=Decimal("99"),
            risk_pct=Decimal("0.5"),
            fee_rate=Decimal("0.0026"),
        )
        self.assertEqual(quantity, Decimal("5.00000000"))
        self.assertLessEqual(quantity * Decimal("1"), Decimal("5"))

    def test_size_is_capped_by_available_cash_at_one_x(self):
        quantity = calculate_spot_quantity(
            equity=Decimal("1000"),
            cash=Decimal("10"),
            entry_estimate=Decimal("100"),
            stop_price=Decimal("99"),
            risk_pct=Decimal("0.5"),
            fee_rate=Decimal("0.0026"),
        )
        self.assertLessEqual(quantity * Decimal("100") * Decimal("1.0026"), Decimal("10"))

    def test_invalid_stop_or_zero_equity_is_rejected(self):
        with self.assertRaises(PaperTradeError):
            calculate_spot_quantity(
                equity=Decimal("1000"), cash=Decimal("1000"),
                entry_estimate=Decimal("100"), stop_price=Decimal("100"),
                risk_pct=Decimal("0.5"), fee_rate=Decimal("0.0026"),
            )
        with self.assertRaises(PaperTradeError):
            calculate_spot_quantity(
                equity=Decimal("0"), cash=Decimal("1000"),
                entry_estimate=Decimal("100"), stop_price=Decimal("99"),
                risk_pct=Decimal("0.5"), fee_rate=Decimal("0.0026"),
            )

    def test_default_pair_universe_is_not_btc_only(self):
        with patch.dict(os.environ, {}, clear=True):
            pairs = configured_pairs()
        self.assertGreater(len(pairs), 1)
        self.assertIn("ETH/USD", pairs)
        self.assertIn("SOL/USD", pairs)

    def test_configured_pairs_support_multiple_crypto_symbols(self):
        with patch.dict(os.environ, {"PAPER_AUTOTRADE_PAIRS": "BTC/USD,ETH/USD,SOL/USD"}, clear=False):
            self.assertEqual(configured_pairs(), ["BTC/USD", "ETH/USD", "SOL/USD"])

    def test_empty_or_malformed_or_non_usd_pair_configuration_fails_closed(self):
        for value in (" ", "BTCUSD", "EUR/JPY"):
            with patch.dict(os.environ, {"PAPER_AUTOTRADE_PAIRS": value}, clear=False):
                with self.assertRaises(PaperTradeError):
                    configured_pairs()

    def test_performance_agent_uses_realized_paper_exit_fills_only(self):
        result = PerformanceAgent().summarize([
            {"status": "filled", "execution_mode": "paper", "side": "SELL", "realized_pnl_usd": "2.50"},
            {"status": "filled", "execution_mode": "paper", "side": "SELL", "realized_pnl_usd": "-1.00"},
            {"status": "filled", "execution_mode": "paper", "side": "BUY", "realized_pnl_usd": None},
            {"status": "filled", "execution_mode": "live", "side": "SELL", "realized_pnl_usd": "99"},
        ])
        self.assertEqual(result["sample_size"], 2)
        self.assertEqual(result["realized_pnl"], 1.5)
        self.assertEqual(result["win_rate_pct"], 50.0)


if __name__ == "__main__":
    unittest.main()
