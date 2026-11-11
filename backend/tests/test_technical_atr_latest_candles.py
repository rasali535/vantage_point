import unittest

from agents.technical_analyst import TechnicalAnalystAgent


class TechnicalAtrWindowTests(unittest.TestCase):
    def test_atr_uses_latest_fourteen_ranges(self):
        candles = [
            {"open": 100, "high": 101, "low": 99, "close": 100}
            for _ in range(30)
        ]
        for index in range(16, 30):
            candles[index] = {"open": 100, "high": 110, "low": 90, "close": 100}
        report = TechnicalAnalystAgent().analyse(candles)
        self.assertEqual(report.atr, 20.0)


if __name__ == "__main__":
    unittest.main()
