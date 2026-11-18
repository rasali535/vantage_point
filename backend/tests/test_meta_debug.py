import unittest

from routes.trading import get_meta_readiness


class RetiredMetaProviderTests(unittest.IsolatedAsyncioTestCase):
    async def test_readiness_reports_deterministic_provider_without_network_call(self):
        result = await get_meta_readiness()
        self.assertEqual(result["status"], "disabled")
        self.assertFalse(result["configured"])
        self.assertEqual(result["provider"], "deterministic")
        self.assertIn("disabled", result["detail"].lower())


if __name__ == "__main__":
    unittest.main()
