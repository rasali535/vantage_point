import asyncio
import unittest
from unittest.mock import patch

from agents.orchestrator import AgentStageTimeout, _run_stage


class AgentStageTimeoutTests(unittest.IsolatedAsyncioTestCase):
    async def test_stage_timeout_identifies_the_failing_agent(self):
        with patch("agents.orchestrator._agent_timeout_seconds", return_value=0.01):
            with self.assertRaises(AgentStageTimeout) as raised:
                await _run_stage("market_intelligence", asyncio.sleep(0.1))

        self.assertEqual(raised.exception.stage, "market_intelligence")
        self.assertEqual(raised.exception.timeout_seconds, 0.01)

    async def test_stage_preserves_provider_failure(self):
        async def fail():
            raise RuntimeError("provider unavailable")

        with patch("agents.orchestrator._agent_timeout_seconds", return_value=0.1):
            with self.assertRaisesRegex(RuntimeError, "provider unavailable"):
                await _run_stage("strategy", fail())


if __name__ == "__main__":
    unittest.main()
