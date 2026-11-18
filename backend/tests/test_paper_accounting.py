from decimal import Decimal

from paper_trading.engine import account_summary, initial_account


def test_account_summary_rebuilds_realized_pnl_from_sell_fills():
    account = initial_account("100.00")
    account["cash"] = "99.98"
    account["realized_pnl"] = "0.06"  # stale legacy accumulator
    account["orders"] = [
        {
            "side": "SELL",
            "realized_pnl_usd": "-0.02",
            "status": "filled",
        }
    ]

    summary = account_summary(account)

    assert summary["realized_pnl"] == "-0.02"
    assert summary["stored_realized_pnl"] == "0.06"
    assert summary["realized_pnl_discrepancy"] == "0.08"
    assert summary["realized_pnl_source"] == "sell_fills"
    assert summary["pnl_reconciliation_status"] == "consistent"


def test_account_summary_uses_legacy_realized_value_only_without_sell_fills():
    account = initial_account("100.00")
    account["realized_pnl"] = "1.25"
    account["orders"] = [
        {"side": "BUY", "realized_pnl_usd": None, "status": "filled"}
    ]

    summary = account_summary(account)

    assert summary["realized_pnl"] == "1.25"
    assert summary["realized_pnl_source"] == "legacy_account_field"


def test_equity_and_total_pnl_reconcile_for_open_position():
    account = initial_account("100.00")
    account["cash"] = "89.99"
    account["positions"] = {
        "EUR/USD": {
            "quantity": "1",
            "average_entry": "10.01",
        }
    }

    summary = account_summary(account, {"EUR/USD": "10.01"})

    assert Decimal(summary["equity"]) - Decimal(summary["initial_equity"]) == Decimal(summary["total_pnl"])
    assert summary["equity_pnl_delta"] == "0.00"
    assert summary["pnl_reconciliation_status"] == "consistent"
