"""Unit tests for the pure momentum signal rules."""
import unittest
from agents.contracts import TradeAction
from paper_trading.momentum_strategy import evaluate_momentum


def candles(count, start=100.0, slope=0.2):
    data = []
    for i in range(count):
        close = start + slope * i
        data.append({"open": close - 0.05, "high": close + 0.1, "low": close - 0.1, "close": close})
    return data


class MomentumStrategyTests(unittest.TestCase):
    def test_aligned_uptrend_returns_buy_and_2r_target(self):
        result = evaluate_momentum(candles(70), candles(70, slope=0.3))
        self.assertEqual(result.action, TradeAction.BUY)
        self.assertGreater(result.atr, 0)
        self.assertAlmostEqual(result.target_distance, result.stop_distance * 2)

    def test_missing_history_fails_closed(self):
        result = evaluate_momentum(candles(20), candles(20))
        self.assertEqual(result.action, TradeAction.HOLD)
        self.assertIsNone(result.stop_distance)

    def test_mixed_trends_hold(self):
        result = evaluate_momentum(candles(70, slope=0.2), candles(70, slope=-0.3))
        self.assertEqual(result.action, TradeAction.HOLD)


if __name__ == "__main__":
    unittest.main()
