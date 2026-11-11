import unittest

from agents.whipsaw_protection import WhipsawProtectionEngine


class LatestCandleWindowTests(unittest.TestCase):
    def test_efficiency_ratio_uses_latest_candles_not_oldest_history(self):
        old = [
            {"open": 100, "high": 100.1, "low": 99.9, "close": 100}
            for _ in range(11)
        ]
        recent = [
            {"open": 100 + i, "high": 101 + i, "low": 99.5 + i, "close": 100 + i}
            for i in range(11)
        ]
        engine = WhipsawProtectionEngine(er_period=10, atr_period=10)
        ratio, regime = engine.calculate_efficiency_ratio(old + recent)
        self.assertEqual(ratio, 1.0)
        self.assertIn("STRONG_TREND", regime)

    def test_atr_uses_latest_candle_window(self):
        old = [
            {"open": 100, "high": 101, "low": 99, "close": 100}
            for _ in range(11)
        ]
        recent = [
            {"open": 100, "high": 110, "low": 90, "close": 100}
            for _ in range(11)
        ]
        engine = WhipsawProtectionEngine(er_period=10, atr_period=10)
        self.assertEqual(engine.calculate_atr(old + recent), 20.0)


if __name__ == "__main__":
    unittest.main()
