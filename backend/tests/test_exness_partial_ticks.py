"""Regression tests for partial Exness tick snapshots and per-symbol freshness."""
import asyncio
import json
import unittest
from unittest.mock import AsyncMock, patch

from markets.providers.exness import ExnessReadOnlyClient
from markets.providers.exness_paper import ExnessPaperMarketData


class FakeSocket:
    def __init__(self):
        self.messages = iter([
            json.dumps({
                "instrument": "EURUSD",
                "bid": 1.08,
                "ask": 1.0802,
                "timestamp": "2026-11-19T12:00:00Z",
            }),
        ])

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def send(self, payload):
        self.subscription = json.loads(payload)

    async def recv(self):
        try:
            return next(self.messages)
        except StopIteration:
            raise asyncio.TimeoutError()


class PartialTickSnapshotTests(unittest.IsolatedAsyncioTestCase):
    async def test_timeout_preserves_ticks_received_before_missing_symbol(self):
        client = object.__new__(ExnessReadOnlyClient)
        client.discover_access_point = AsyncMock(return_value="https://access.example")
        client._signed_get_headers = lambda path: {}

        with patch("websockets.connect", return_value=FakeSocket()):
            ticks = await client.get_ticks(["EURUSD", "GBPUSD"])

        self.assertEqual([tick["instrument"] for tick in ticks], ["EURUSD"])
        self.assertEqual(ticks[0]["bid"], 1.08)

    async def test_refresh_records_freshness_only_for_received_instruments(self):
        class Client:
            requested = None

            async def get_ticks(self, instruments):
                self.requested = list(instruments)
                return [{
                    "instrument": "EURUSD",
                    "bid": 1.08,
                    "ask": 1.0802,
                    "timestamp": "2026-11-19T12:00:00Z",
                }]

        provider = ExnessPaperMarketData(client=Client())
        await provider.refresh_ticks(["EUR/USD", "GBP/USD", "USD/JPY"])

        self.assertEqual(provider._client.requested, ["EURUSD", "GBPUSD"])
        self.assertIn("EURUSD", provider._tick_refreshed_at)
        self.assertNotIn("GBPUSD", provider._tick_refreshed_at)
        self.assertIn("EURUSD", provider._ticks)
        self.assertNotIn("GBPUSD", provider._ticks)


if __name__ == "__main__":
    unittest.main()
