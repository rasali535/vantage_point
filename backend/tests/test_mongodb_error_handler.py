import asyncio
import json
import unittest
from types import SimpleNamespace

from pymongo.errors import OperationFailure

from main import mongodb_unavailable_handler


class MongoDBErrorHandlerTests(unittest.TestCase):
    def test_handler_returns_safe_503_and_logs_diagnostic_context(self):
        request = SimpleNamespace(
            method="GET",
            url=SimpleNamespace(path="/api/trading/status"),
        )
        exc = OperationFailure("sensitive driver detail", code=13)

        with self.assertLogs("main", level="ERROR") as captured:
            response = asyncio.run(mongodb_unavailable_handler(request, exc))

        self.assertEqual(response.status_code, 503)
        payload = json.loads(response.body)
        self.assertIn("request_id", payload)
        self.assertEqual(
            payload["detail"],
            "MongoDB is temporarily unavailable. No trading action was executed.",
        )
        log_output = "\n".join(captured.output)
        self.assertIn("mongodb_operation_failed", log_output)
        self.assertIn("OperationFailure", log_output)
        self.assertIn("/api/trading/status", log_output)
        self.assertIn("code=13", log_output)
        self.assertNotIn("sensitive driver detail", log_output)


if __name__ == "__main__":
    unittest.main()
