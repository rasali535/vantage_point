import asyncio
import os
import unittest
from unittest.mock import AsyncMock, patch

import httpx

from markets.providers.twelve_data import (
    TwelveDataAPIError,
    TwelveDataConfigurationError,
    TwelveDataReadOnlyClient,
)


class _ClientContext:
    def __init__(self, response):
        self._response = response
        self.get = AsyncMock(return_value=response)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


class TwelveDataReadOnlyTests(unittest.TestCase):
    def test_missing_api_key_fails_closed(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(TwelveDataConfigurationError):
                TwelveDataReadOnlyClient()

    def test_symbol_and_interval_allowlists(self):
        client = TwelveDataReadOnlyClient(api_key="test-key")
        with self.assertRaises(TwelveDataConfigurationError):
            client.validate_symbol("AAPL")
        with self.assertRaises(TwelveDataConfigurationError):
            client.validate_interval("1day")

    def test_candle_count_is_bounded(self):
        client = TwelveDataReadOnlyClient(api_key="test-key")
        with self.assertRaises(TwelveDataConfigurationError):
            asyncio.run(client.get_candles("EUR/USD", "15min", 501))

    def test_time_series_request_normalizes_ascending_ohlc(self):
        response = httpx.Response(200, json={
            "meta": {"symbol": "EUR/USD"},
            "values": [
                {"datetime": "2026-11-25 10:15:00", "open": "1.1000", "high": "1.1020", "low": "1.0990", "close": "1.1010", "volume": "0"},
                {"datetime": "2026-11-25 10:00:00", "open": "1.0980", "high": "1.1010", "low": "1.0970", "close": "1.1000", "volume": "0"},
            ],
        })
        fake = _ClientContext(response)
        client = TwelveDataReadOnlyClient(api_key="test-key")
        with patch("httpx.AsyncClient", return_value=fake):
            candles = asyncio.run(client.get_candles("EUR/USD", "15min", 120))
        self.assertEqual(len(candles), 2)
        self.assertLess(candles[0]["timestamp"], candles[1]["timestamp"])
        self.assertEqual(candles[0]["close"], 1.1)
        args = fake.get.await_args
        self.assertEqual(args.args[0], "https://api.twelvedata.com/time_series")
        self.assertEqual(args.kwargs["params"]["symbol"], "EUR/USD")
        self.assertEqual(args.kwargs["params"]["interval"], "15min")
        self.assertEqual(args.kwargs["params"]["outputsize"], 120)
        self.assertEqual(args.kwargs["params"]["timezone"], "UTC")
        self.assertEqual(args.kwargs["params"]["apikey"], "test-key")

    def test_invalid_ohlc_rows_are_discarded(self):
        response = httpx.Response(200, json={
            "values": [
                {"datetime": "2026-11-25 10:15:00", "open": "1.10", "high": "1.09", "low": "1.08", "close": "1.11"},
                {"datetime": "2026-11-25 10:00:00", "open": "1.10", "high": "1.12", "low": "1.08", "close": "1.11"},
            ],
        })
        fake = _ClientContext(response)
        client = TwelveDataReadOnlyClient(api_key="test-key")
        with patch("httpx.AsyncClient", return_value=fake):
            candles = asyncio.run(client.get_candles("EUR/USD", "15min", 2))
        self.assertEqual(len(candles), 1)

    def test_provider_error_does_not_echo_provider_message_or_api_key(self):
        response = httpx.Response(200, json={
            "status": "error",
            "code": 401,
            "message": "invalid apikey test-key",
        })
        fake = _ClientContext(response)
        client = TwelveDataReadOnlyClient(api_key="test-key")
        with patch("httpx.AsyncClient", return_value=fake):
            with self.assertRaises(TwelveDataAPIError) as raised:
                asyncio.run(client.get_candles("EUR/USD"))
        self.assertNotIn("test-key", str(raised.exception))
        self.assertNotIn("invalid apikey", str(raised.exception))

    def test_rate_limit_is_reported_without_retrying(self):
        response = httpx.Response(429)
        fake = _ClientContext(response)
        client = TwelveDataReadOnlyClient(api_key="test-key")
        with patch("httpx.AsyncClient", return_value=fake):
            with self.assertRaisesRegex(TwelveDataAPIError, "rate limit"):
                asyncio.run(client.get_quote("XAU/USD"))
        fake.get.assert_awaited_once()

    def test_quote_uses_mid_when_provider_does_not_supply_bid_ask(self):
        response = httpx.Response(200, json={
            "symbol": "GBP/USD",
            "price": "1.27000",
            "datetime": "2026-11-25 10:15:00",
        })
        fake = _ClientContext(response)
        client = TwelveDataReadOnlyClient(api_key="test-key")
        with patch("httpx.AsyncClient", return_value=fake):
            quote = asyncio.run(client.get_quote("GBP/USD"))
        self.assertEqual(quote["bid"], 1.27)
        self.assertEqual(quote["ask"], 1.27)
        self.assertEqual(quote["last"], 1.27)
        self.assertTrue(quote["read_only"])
        self.assertFalse(quote["execution_enabled"])


if __name__ == "__main__":
    unittest.main()
