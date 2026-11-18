import unittest
from unittest.mock import patch

from routes.trading import get_models_readiness


class ModelReadinessTests(unittest.IsolatedAsyncioTestCase):
    async def test_readiness_reports_deterministic_controls_and_huggingface_provider(self):
        with patch("agents.huggingface_client.huggingface_client.configured", True):
            result = await get_models_readiness()
        self.assertEqual(result["provider"], "huggingface")
        self.assertEqual(result["decision_engine"], "deterministic")
        self.assertEqual(result["risk_engine"], "deterministic_and_authoritative")
        self.assertEqual(result["execution_mode"], "paper_only")


if __name__ == "__main__":
    unittest.main()
