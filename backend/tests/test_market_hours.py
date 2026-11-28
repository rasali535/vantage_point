import os
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from paper_trading.market_hours import market_entry_block_reason


def data(now):
    stamp = now.timestamp()
    candles15 = [{"timestamp": stamp - 60}]
    candles1h = [{"timestamp": stamp - 3600}]
    ticker = {"timestamp": now.isoformat(), "last": 2000}
    return ticker, candles15, candles1h


class MarketHoursGateTests(unittest.TestCase):
    def test_friday_metal_entry_is_blocked_before_early_close(self):
        now = datetime(2026, 11, 27, 19, 31, tzinfo=timezone.utc)
        ticker, m15, h1 = data(now)
        self.assertIn("Friday entry cutoff", market_entry_block_reason("XAU/USD", ticker, m15, h1, now=now))

    def test_friday_fx_cutoff_uses_configured_buffer(self):
        now = datetime(2026, 11, 27, 20, 10, tzinfo=timezone.utc)
        ticker, m15, h1 = data(now)
        self.assertIn("Friday entry cutoff", market_entry_block_reason("EUR/USD", ticker, m15, h1, now=now))

    def test_saturday_is_blocked(self):
        now = datetime(2026, 11, 28, 14, 0, tzinfo=timezone.utc)
        ticker, m15, h1 = data(now)
        self.assertIn("Weekend", market_entry_block_reason("XAU/USD", ticker, m15, h1, now=now))

    def test_sunday_before_metal_reopen_is_blocked(self):
        now = datetime(2026, 11, 29, 22, 59, tzinfo=timezone.utc)
        ticker, m15, h1 = data(now)
        self.assertIn("has not reopened", market_entry_block_reason("XAU/USD", ticker, m15, h1, now=now))

    def test_missing_or_stale_quote_fails_closed(self):
        now = datetime(2026, 11, 30, 12, 0, tzinfo=timezone.utc)
        ticker, m15, h1 = data(now)
        ticker.pop("timestamp")
        self.assertIn("timestamp is missing", market_entry_block_reason("EUR/USD", ticker, m15, h1, now=now))

    def test_stale_candle_fails_closed(self):
        now = datetime(2026, 11, 30, 12, 0, tzinfo=timezone.utc)
        ticker, m15, h1 = data(now)
        m15[-1]["timestamp"] = (now.timestamp() - 3601)
        self.assertIn("M15 candle is stale", market_entry_block_reason("EUR/USD", ticker, m15, h1, now=now))

    def test_holiday_blackout_override_blocks_pair(self):
        now = datetime(2026, 12, 24, 12, 0, tzinfo=timezone.utc)
        ticker, m15, h1 = data(now)
        cfg = '[{"start":"2026-12-24T11:00:00Z","end":"2026-12-24T13:00:00Z","pairs":["XAU/USD"]}]'
        with patch.dict(os.environ, {"PAPER_MARKET_CLOSED_WINDOWS_UTC": cfg}):
            self.assertIn("blackout", market_entry_block_reason("XAU/USD", ticker, m15, h1, now=now))

    def test_malformed_holiday_config_fails_closed(self):
        now = datetime(2026, 11, 30, 12, 0, tzinfo=timezone.utc)
        ticker, m15, h1 = data(now)
        with patch.dict(os.environ, {"PAPER_MARKET_CLOSED_WINDOWS_UTC": "not-json"}):
            self.assertIn("configuration is invalid", market_entry_block_reason("EUR/USD", ticker, m15, h1, now=now))


if __name__ == "__main__":
    unittest.main()
