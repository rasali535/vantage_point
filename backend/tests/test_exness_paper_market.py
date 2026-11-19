import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock

from markets.providers.exness_paper import ExnessPaperMarketData


class FakeExnessClient:
    def __init__(self):
        self.get_ticks = AsyncMock(return_value=[
            {"instrument": "XAUUSD", "bid": 2000.0, "ask": 2000.2, "timestamp": "2026-11-18T12:00:00Z"},
            {"instrument": "EURUSD", "bid": 1.08, "ask": 1.0802, "timestamp": "2026-11-18T12:00:00Z"},
        ])
        self.get_candles = AsyncMock(return_value=[
            {
                "time": "2026-11-18T12:00:00+00:00",
                "bid": {"open": 2000.0, "high": 2002.0, "low": 1999.0, "close": 2001.0},
                "ask": {"open": 2000.2, "high": 2002.2, "low": 1999.2, "close": 2001.2},
                "volume": 12,
            }
            for _ in range(35)
        ])


class ExnessPaperMarketDataTests(unittest.IsolatedAsyncioTestCase):
    async def test_refresh_ticks_maps_exness_prices_to_paper_ticker(self):
        client = FakeExnessClient()
        market = ExnessPaperMarketData(client=client)

        await market.refresh_ticks(["XAU/USD", "EUR/USD"])
        ticker = await market.get_ticker("XAU/USD")

        self.assertEqual(ticker["source"], "exness_read_only")
        self.assertEqual(ticker["bid"], 2000.0)
        self.assertEqual(ticker["ask"], 2000.2)
        self.assertAlmostEqual(ticker["last"], 2000.1)
        client.get_ticks.assert_awaited_once_with(["XAUUSD", "EURUSD"])

    async def test_ohlc_uses_midpoint_of_exness_bid_and_ask_candles(self):
        client = FakeExnessClient()
        market = ExnessPaperMarketData(client=client)

        candles = await market.get_ohlc("XAU/USD", interval=1)

        self.assertEqual(len(candles), 35)
        self.assertEqual(candles[0]["open"], 2000.1)
        self.assertEqual(candles[0]["high"], 2002.1)
        self.assertEqual(candles[0]["low"], 1999.1)
        self.assertEqual(candles[0]["close"], 2001.1)
        self.assertEqual(
            candles[0]["timestamp"],
            int(datetime(2026, 11, 18, 12, 0, tzinfo=timezone.utc).timestamp()),
        )
        client.get_candles.assert_awaited_once_with(
            "XAUUSD", timeframe="M1", count=120, price_type="both"
        )

    async def test_candle_history_is_cached_between_scans(self):
        client = FakeExnessClient()
        client.get_candles.return_value = client.get_candles.return_value * 2
        market = ExnessPaperMarketData(client=client)
        first = await market.get_ohlc("XAU/USD", interval=15)
        second = await market.get_ohlc("XAU/USD", interval=15)
        self.assertEqual(first, second)
        client.get_candles.assert_awaited_once_with("XAUUSD", timeframe="M15", count=120, price_type="both")

    async def test_fails_closed_for_symbols_outside_initial_exness_allowlist(self):
        market = ExnessPaperMarketData(client=FakeExnessClient())
        with self.assertRaises(ValueError):
            await market.get_ticker("USD/JPY")

    async def test_fails_closed_when_exness_returns_too_few_candles(self):
        client = FakeExnessClient()
        client.get_candles = AsyncMock(return_value=[])
        market = ExnessPaperMarketData(client=client)

        with self.assertRaisesRegex(RuntimeError, "at least 30"):
            await market.get_ohlc("EUR/USD", interval=5)


if __name__ == "__main__":
    unittest.main()
