from datetime import datetime, timedelta, timezone

from paper_trading.reentry import reentry_cooldown_remaining


def test_stop_loss_uses_fifteen_minute_cooldown(monkeypatch):
    monkeypatch.delenv("PAPER_AUTOTRADING_STOP_COOLDOWN_SECONDS", raising=False)
    now = datetime(2026, 11, 18, 20, 0, tzinfo=timezone.utc)
    orders = [{
        "pair": "XPT/USD", "side": "SELL", "status": "filled",
        "triggered_by": "stop_loss",
        "timestamp": (now - timedelta(minutes=5)).isoformat(),
    }]

    assert reentry_cooldown_remaining(orders, "XPT/USD", now) == 600


def test_non_stop_exit_uses_shorter_cooldown(monkeypatch):
    monkeypatch.delenv("PAPER_AUTOTRADING_REENTRY_COOLDOWN_SECONDS", raising=False)
    now = datetime(2026, 11, 18, 20, 0, tzinfo=timezone.utc)
    orders = [{
        "pair": "EUR/USD", "side": "SELL", "status": "filled",
        "timestamp": (now - timedelta(seconds=60)).isoformat(),
    }]

    assert reentry_cooldown_remaining(orders, "EUR/USD", now) == 120


def test_cooldown_expires_and_does_not_block_other_pairs():
    now = datetime(2026, 11, 18, 20, 0, tzinfo=timezone.utc)
    orders = [{
        "pair": "XAG/USD", "side": "SELL", "status": "filled",
        "triggered_by": "stop_loss",
        "timestamp": (now - timedelta(minutes=20)).isoformat(),
    }]

    assert reentry_cooldown_remaining(orders, "XAG/USD", now) == 0
    assert reentry_cooldown_remaining(orders, "XPT/USD", now) == 0


def test_missing_exit_timestamp_fails_closed():
    orders = [{
        "pair": "XCU/USD", "side": "SELL", "status": "filled",
        "triggered_by": "stop_loss",
    }]

    assert reentry_cooldown_remaining(orders, "XCU/USD") == 900
