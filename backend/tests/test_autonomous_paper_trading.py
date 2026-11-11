import os
import unittest
from decimal import Decimal
from unittest.mock import patch

from paper_trading.autopilot import calculate_spot_quantity, configured_pairs
from paper_trading.engine import PaperTradeError


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

    def test_configured_pairs_support_multiple_crypto_symbols(self):
        with patch.dict(os.environ, {"PAPER_AUTOTRADE_PAIRS": "BTC/USD,ETH/USD,SOL/USD"}, clear=False):
            self.assertEqual(configured_pairs(), ["BTC/USD", "ETH/USD", "SOL/USD"])

    def test_empty_or_malformed_pair_configuration_fails_closed(self):
        with patch.dict(os.environ, {"PAPER_AUTOTRADE_PAIRS": " "}, clear=False):
            with self.assertRaises(PaperTradeError):
                configured_pairs()
        with patch.dict(os.environ, {"PAPER_AUTOTRADE_PAIRS": "BTCUSD"}, clear=False):
            with self.assertRaises(PaperTradeError):
                configured_pairs()


if __name__ == "__main__":
    unittest.main()
