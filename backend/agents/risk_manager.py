"""Risk analyst advisory. Deterministic risk controls remain authoritative."""
import json
import os
from agents.contracts import AgentFinding
from agents.meta_ai import meta_ai, DEFAULT_META_MODEL


class RiskManagerAgent:
    name = "risk_manager"

    async def assess(self, pair: str, ticker: dict, technical: dict, portfolio: dict) -> AgentFinding:
        response = await meta_ai.chat(
            model=os.getenv("RISK_MODEL", DEFAULT_META_MODEL),
            system_prompt=(
                "You are the Risk Manager advisory agent. Identify uncertainty, liquidity, volatility "
                "and downside scenarios from supplied facts only. You cannot approve orders or override "
                "deterministic risk controls. Return JSON: summary, evidence[], confidence (0..1), warnings[]."
            ),
            user_prompt=json.dumps({"pair": pair, "ticker": ticker, "technical": technical, "portfolio": portfolio}, default=str),
        )
        try:
            return AgentFinding(agent=self.name, **json.loads(response))
        except Exception as exc:
            raise RuntimeError("Risk Manager returned an invalid structured assessment.") from exc
