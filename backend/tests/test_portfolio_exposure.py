from decimal import Decimal

import pytest

from paper_trading.autopilot import _portfolio_exposure_usd


def test_portfolio_exposure_uses_live_marks():
    account = {
        "positions": {
            "XAU/USD": {"quantity": "0.01", "average_entry": "2000"},
            "EUR/USD": {"quantity": "1000", "average_entry": "1.08"},
        }
    }
    marks = {"XAU/USD": Decimal("2010"), "EUR/USD": Decimal("1.09")}

    assert _portfolio_exposure_usd(account, marks) == Decimal("3110.00")


def test_portfolio_exposure_falls_back_to_entry_when_mark_is_missing():
    account = {
        "positions": {
            "XAU/USD": {"quantity": "0.01", "average_entry": "2000"},
        }
    }

    assert _portfolio_exposure_usd(account, {}) == Decimal("20.00")


def test_portfolio_exposure_rejects_invalid_position_data():
    account = {
        "positions": {
            "XAU/USD": {"quantity": "-1", "average_entry": "2000"},
        }
    }

    with pytest.raises(Exception, match="invalid position data"):
        _portfolio_exposure_usd(account, {})
