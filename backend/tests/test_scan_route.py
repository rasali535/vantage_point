import unittest
from unittest.mock import patch

from fastapi import HTTPException

from agents.orchestrator import AgentStageTimeout
from routes.trading import scan_and_analyze_route


class ScanRouteTimeoutTests(unittest.IsolatedAsyncioTestCase):
    async def test_stage_timeout_returns_actionable_503(self):
        with patch(
            "routes.trading.scan_and_analyze",
            side_effect=AgentStageTimeout("market_intelligence", 90.0),
        ):
            with self.assertRaises(HTTPException) as raised:
                await scan_and_analyze_route()
        self.assertEqual(raised.exception.status_code, 503)
        detail = raised.exception.detail
        self.assertEqual(detail["error_code"], "agent_stage_timeout")
        self.assertIn("market_intelligence", detail["message"])
        self.assertIn("request_id", detail)


if __name__ == "__main__":
    unittest.main()
