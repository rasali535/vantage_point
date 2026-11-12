import hashlib
import os
import unittest
from unittest.mock import patch

from routes.trading import debug_meta_upstream


class FakeResponse:
    def __init__(self, status_code, text, content_type="application/json"):
        self.status_code = status_code
        self.text = text
        self.headers = {"content-type": content_type}


class FakeAsyncClient:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def get(self, url, headers=None):
        assert url.endswith("/models")
        assert headers["Authorization"].startswith("Bearer ")
        return FakeResponse(200, '{"object":"list","data":[{"id":"muse-spark-1.3"}]}')

    async def post(self, url, headers=None, json=None):
        assert url.endswith("/chat/completions")
        assert json["model"] == "muse-spark-1.3"
        return FakeResponse(200, '{"id":"chatcmpl-x","choices":[{"message":{"content":"OK"}}]}')


class MetaDebugUpstreamTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.test_key = "DEBUG_probe_key_999"
        self.env_patch = patch.dict(os.environ, {"MODEL_API_KEY": self.test_key})
        self.env_patch.start()

    def tearDown(self):
        self.env_patch.stop()

    async def test_debug_reports_upstream_results_without_leaking_key(self):
        fake_addrs = [
            (2, 1, 6, "", ("93.184.216.34", 443)),
            (10, 1, 6, "", ("2606:2800:220:1:248:1893:25c8:1946", 443, 0, 0)),
        ]
        with patch("routes.trading.httpx.AsyncClient", FakeAsyncClient), \
             patch("routes.trading.socket.getaddrinfo", return_value=fake_addrs):
            report = await debug_meta_upstream()
        self.assertTrue(report["key_configured"])
        expected_fp = hashlib.sha256(self.test_key.encode("utf-8")).hexdigest()[:16]
        self.assertEqual(report["key_fingerprint"], expected_fp)
        self.assertEqual(report["base_url"], "https://api.meta.ai/v1")
        self.assertEqual(len(report["dns_api_meta_ai"]), 2)
        self.assertEqual(report["request_headers"]["Authorization"], "<redacted-present>")
        self.assertEqual(report["get_models"]["http_status"], 200)
        self.assertIn("muse-spark-1.3", report["get_models"]["body_prefix"])
        self.assertEqual(report["post_chat_completions"]["http_status"], 200)
        self.assertEqual(report["chat_payload_sent"]["model"], "muse-spark-1.3")
        self.assertNotIn(self.test_key, str(report))

    async def test_debug_without_key_reports_not_configured(self):
        with patch.dict(os.environ, {"MODEL_API_KEY": ""}):
            with patch("routes.trading.httpx.AsyncClient", FakeAsyncClient), \
                 patch("routes.trading.socket.getaddrinfo", side_effect=RuntimeError("no dns")):
                report = await debug_meta_upstream()
        self.assertFalse(report["key_configured"])
        self.assertEqual(report["key_fingerprint"], "missing")
        self.assertNotIn("Authorization", report["request_headers"])
        self.assertIn("error", report["dns_api_meta_ai"])


if __name__ == "__main__":
    unittest.main()
