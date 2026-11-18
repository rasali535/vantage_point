import base64
import hashlib
import json
import os
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from markets.providers.exness import ExnessConfigurationError, ExnessReadOnlyClient, _base_url, _load_private_key


class ExnessReadOnlyTests(unittest.TestCase):
    def test_exness_base_url_rejects_non_https_and_non_origin_urls(self):
        for value in (
            "http://gateway.example",
            "https://user:pass@gateway.example",
            "https://gateway.example/path",
            "https://gateway.example/?query=1",
            "https://gateway.example/#fragment",
        ):
            with self.subTest(value=value):
                with self.assertRaises(ExnessConfigurationError):
                    _base_url(value)

    def test_exness_base_url_accepts_gateway_and_discovered_access_point_hosts(self):
        self.assertEqual(_base_url("https://gateway.example/"), "https://gateway.example")
        self.assertEqual(_base_url("https://access-point.example"), "https://access-point.example")

    def test_load_generated_hex_ed25519_key(self):
        key = Ed25519PrivateKey.generate()
        seed = key.private_bytes(
            serialization.Encoding.Raw,
            serialization.PrivateFormat.Raw,
            serialization.NoEncryption(),
        )
        public = key.public_key().public_bytes(
            serialization.Encoding.Raw,
            serialization.PublicFormat.Raw,
        )
        loaded = _load_private_key((seed + public).hex())
        self.assertIsInstance(loaded, Ed25519PrivateKey)

    def test_signed_get_headers_match_exness_documented_shape(self):
        key = Ed25519PrivateKey.generate()
        seed = key.private_bytes(
            serialization.Encoding.Raw,
            serialization.PrivateFormat.Raw,
            serialization.NoEncryption(),
        )
        public = key.public_key().public_bytes(
            serialization.Encoding.Raw,
            serialization.PublicFormat.Raw,
        )
        env = {
            "EXN_API_KEY": "exnsk-test",
            "EXN_PRIVATE_KEY": (seed + public).hex(),
            "EXN_ACCOUNT_ID": "123456",
            "EXN_DISCOVERY_BASE_URL": "https://gateway.example",
            "EXN_READ_ONLY": "true",
        }
        with patch.dict(os.environ, env, clear=False):
            client = ExnessReadOnlyClient()
        path = "/v1/trading/access-point?account_id=123456"
        headers = client._signed_get_headers(path)
        encoded_payload = headers["EXN-DATA"]
        payload_bytes = base64.urlsafe_b64decode(encoded_payload + "=" * (-len(encoded_payload) % 4))
        payload = json.loads(payload_bytes)
        self.assertEqual(payload["method"], "GET")
        self.assertEqual(payload["path"], path)
        self.assertEqual(payload["idempotency_key"], "")
        self.assertEqual(headers["EXN-IDEMPOTENCY-KEY"], "")
        self.assertEqual(
            payload["body_hash"],
            "47DEQpj8HBSa-_TImW-5JCeuQeRkm5NMpJWZG3hSuFU",
        )
        signature = base64.urlsafe_b64decode(
            headers["EXN-SIGN"] + "=" * (-len(headers["EXN-SIGN"]) % 4)
        )
        client.private_key.public_key().verify(signature, payload_bytes)

    def test_market_data_allowlist_rejects_other_instruments(self):
        key = Ed25519PrivateKey.generate()
        seed = key.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())
        public = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        env = {
            "EXN_API_KEY": "exnsk-test",
            "EXN_PRIVATE_KEY": (seed + public).hex(),
            "EXN_ACCOUNT_ID": "123456",
            "EXN_DISCOVERY_BASE_URL": "https://gateway.example",
            "EXN_READ_ONLY": "true",
        }
        with patch.dict(os.environ, env, clear=False):
            client = ExnessReadOnlyClient()
        import asyncio
        with self.assertRaises(ExnessConfigurationError):
            asyncio.run(client.get_candles("AAPL"))
        with self.assertRaises(ExnessConfigurationError):
            asyncio.run(client.get_ticks(["XAUUSD", "AAPL"]))

    def test_candle_request_rejects_invalid_timeframe_and_count(self):
        key = Ed25519PrivateKey.generate()
        seed = key.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())
        public = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        env = {
            "EXN_API_KEY": "exnsk-test",
            "EXN_PRIVATE_KEY": (seed + public).hex(),
            "EXN_ACCOUNT_ID": "123456",
            "EXN_DISCOVERY_BASE_URL": "https://gateway.example",
            "EXN_READ_ONLY": "true",
        }
        with patch.dict(os.environ, env, clear=False):
            client = ExnessReadOnlyClient()
        import asyncio
        with self.assertRaises(ExnessConfigurationError):
            asyncio.run(client.get_candles("XAUUSD", "TICK", 100))
        with self.assertRaises(ExnessConfigurationError):
            asyncio.run(client.get_candles("XAUUSD", "M15", 501))

    def test_client_refuses_non_readonly_mode(self):
        with patch.dict(os.environ, {"EXN_READ_ONLY": "false"}, clear=False):
            with self.assertRaises(ExnessConfigurationError):
                ExnessReadOnlyClient()


if __name__ == "__main__":
    unittest.main()
