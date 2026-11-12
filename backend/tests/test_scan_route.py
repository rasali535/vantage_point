import unittest
from unittest.mock import patch

from fastapi import HTTPException

from pydantic import ValidationError

from agents.orchestrator import AgentStageTimeout
from routes.trading import ScanRequest, scan_and_analyze_route


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


class ScanRequestValidationTests(unittest.TestCase):
    def test_pair_defaults_to_none(self):
        self.assertIsNone(ScanRequest().pair)

    def test_pair_normalizes_case_and_whitespace(self):
        self.assertEqual(ScanRequest(pair="  eth/usd ").pair, "ETH/USD")

    def test_pair_rejects_malformed_values(self):
        for bad in ("bad!!", "BTC", "BTC/USD/X", "BTC/", "/USD", "x" * 21):
            with self.subTest(pair=bad):
                with self.assertRaises(ValidationError):
                    ScanRequest(pair=bad)


class ScanRoutePairTests(unittest.IsolatedAsyncioTestCase):
    async def test_requested_pair_is_forwarded(self):
        with patch("routes.trading.scan_and_analyze", return_value={"decision": {}}) as mock_scan:
            await scan_and_analyze_route(ScanRequest(pair="ETH/USD"))
            mock_scan.assert_awaited_once_with(pair="ETH/USD")

    async def test_absent_body_preserves_default(self):
        with patch("routes.trading.scan_and_analyze", return_value={"decision": {}}) as mock_scan:
            await scan_and_analyze_route()
            mock_scan.assert_awaited_once_with(pair=None)


if __name__ == "__main__":
    unittest.main()
