from decimal import Decimal

from paper_trading.engine import account_summary, initial_account


def test_account_summary_rebuilds_realized_pnl_from_cash_accurate_fill_replay():
    account = initial_account("100.00")
    account["cash"] = "99.98"
    account["realized_pnl"] = "0.06"  # stale legacy accumulator
    account["orders"] = [
        {
            "pair": "EUR/USD", "side": "BUY", "quantity": "1",
            "fill_price": "10.00", "gross_usd": "10.00", "fee_usd": "0.00",
            "realized_pnl_usd": None, "status": "filled",
        },
        {
            "pair": "EUR/USD", "side": "SELL", "quantity": "1",
            "fill_price": "9.98", "gross_usd": "9.98", "fee_usd": "0.00",
            "realized_pnl_usd": "-0.02", "status": "filled",
        }
    ]

    summary = account_summary(account)

    assert summary["realized_pnl"] == "-0.02"
    assert summary["stored_realized_pnl"] == "0.06"
    assert summary["realized_pnl_discrepancy"] == "0.08"
    assert summary["realized_pnl_source"] == "replayed_fills"
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


def test_fill_replay_captures_fractional_cent_fees_and_notional_rounding():
    account = initial_account("100.00")
    account["orders"] = [
        {
            "pair": "XAG/USD", "side": "BUY", "quantity": "1",
            "fill_price": "10.004", "gross_usd": "10.004",
            "fee_usd": "0.001", "realized_pnl_usd": None,
        },
        {
            "pair": "XAG/USD", "side": "SELL", "quantity": "1",
            "fill_price": "10.000", "gross_usd": "10.000",
            "fee_usd": "0.001", "realized_pnl_usd": "0.00",
        },
    ]

    summary = account_summary(account)

    assert Decimal(summary["realized_pnl"]) == Decimal("-0.006")
    assert summary["realized_pnl_source"] == "replayed_fills"
