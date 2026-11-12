import asyncio
import os
import unittest
from unittest.mock import patch

from agents.orchestrator import AgentStageTimeout, _agent_timeout_seconds, _run_stage


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


class AgentTimeoutConfigTests(unittest.TestCase):
    def test_default_budget(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(_agent_timeout_seconds(), 90.0)

    def test_env_override_and_clamps(self):
        with patch.dict(os.environ, {"AGENT_TIMEOUT_SECONDS": "45"}):
            self.assertEqual(_agent_timeout_seconds(), 45.0)
        with patch.dict(os.environ, {"AGENT_TIMEOUT_SECONDS": "garbage"}):
            self.assertEqual(_agent_timeout_seconds(), 90.0)
        with patch.dict(os.environ, {"AGENT_TIMEOUT_SECONDS": "1"}):
            self.assertEqual(_agent_timeout_seconds(), 10.0)
        with patch.dict(os.environ, {"AGENT_TIMEOUT_SECONDS": "9999"}):
            self.assertEqual(_agent_timeout_seconds(), 120.0)


if __name__ == "__main__":
    unittest.main()
