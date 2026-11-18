from decimal import Decimal
import unittest

from paper_trading.autopilot import _portfolio_exposure_usd
from paper_trading.engine import PaperTradeError


class PortfolioExposureTests(unittest.TestCase):
    def test_portfolio_exposure_uses_live_marks(self):
        account = {
            "positions": {
                "XAU/USD": {"quantity": "0.01", "average_entry": "2000"},
                "EUR/USD": {"quantity": "1000", "average_entry": "1.08"},
            }
        }
        marks = {"XAU/USD": Decimal("2010"), "EUR/USD": Decimal("1.09")}

        self.assertEqual(
            _portfolio_exposure_usd(account, marks),
            Decimal("1110.10"),
        )

    def test_portfolio_exposure_falls_back_to_entry_when_mark_is_missing(self):
        account = {
            "positions": {
                "XAU/USD": {"quantity": "0.01", "average_entry": "2000"},
            }
        }

        self.assertEqual(
            _portfolio_exposure_usd(account, {}),
            Decimal("20.00"),
        )

    def test_portfolio_exposure_rejects_invalid_position_data(self):
        account = {
            "positions": {
                "XAU/USD": {"quantity": "-1", "average_entry": "2000"},
            }
        }

        with self.assertRaisesRegex(PaperTradeError, "invalid position data"):
            _portfolio_exposure_usd(account, {})


if __name__ == "__main__":
    unittest.main()
