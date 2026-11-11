import os
import unittest
from unittest.mock import patch

from fastapi import HTTPException

import database
from agents.kraken import KrakenAgent
from routes.trading import manual_trade


class TradingSafetyTests(unittest.IsolatedAsyncioTestCase):
    async def test_database_missing_uri_fails_closed(self):
        with patch.object(database, "MONGODB_URL", None), patch.object(database, "_client", None), patch.object(database, "_database", None):
            with self.assertRaises(HTTPException) as raised:
                await database.get_database()
        self.assertEqual(raised.exception.status_code, 503)

    async def test_private_account_reads_are_disabled_by_default(self):
        with patch.dict(os.environ, {"KRAKEN_ACCOUNT_READS_ENABLED": "false"}):
            agent = KrakenAgent()
            with self.assertRaisesRegex(RuntimeError, "disabled"):
                await agent.get_balance()

    async def test_order_placement_is_disabled(self):
        agent = KrakenAgent()
        with self.assertRaisesRegex(RuntimeError, "Order placement is disabled"):
            await agent.execute_trade("BTC/USD", "buy", 0.001)

    async def test_manual_trade_endpoint_is_locked(self):
        with self.assertRaises(HTTPException) as raised:
            await manual_trade(None)
        self.assertEqual(raised.exception.status_code, 423)


if __name__ == "__main__":
    unittest.main()
