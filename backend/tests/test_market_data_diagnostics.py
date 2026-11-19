import unittest

from paper_trading.autopilot import _market_error_summary


class MarketDataDiagnosticsTests(unittest.TestCase):
    def test_market_error_summary_keeps_status_and_redacts_credentials(self):
        detail = _market_error_summary(RuntimeError(
            "Exness API returned HTTP 401; access_token=super-secret Bearer abc123"
        ))
        self.assertIn("HTTP 401", detail)
        self.assertIn("access_token=[redacted]", detail)
        self.assertIn("Bearer [redacted]", detail)
        self.assertNotIn("super-secret", detail)
        self.assertNotIn("abc123", detail)

    def test_market_error_summary_is_bounded_and_handles_empty_messages(self):
        self.assertEqual(_market_error_summary(RuntimeError("")), "No error detail supplied.")
        self.assertLessEqual(len(_market_error_summary(RuntimeError("x" * 500))), 240)


if __name__ == "__main__":
    unittest.main()
