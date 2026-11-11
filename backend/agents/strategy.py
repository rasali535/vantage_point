"""Strategy agent synthesizes findings into a human-review proposal only."""
import json
import os
from agents.contracts import StrategyProposal
from agents.meta_ai import meta_ai, DEFAULT_META_MODEL


class StrategyAgent:
    name = "strategy"

    async def propose(self, market: dict, technical: dict, risk: dict) -> StrategyProposal:
        response = await meta_ai.chat(
            model=os.getenv("TRADING_MODEL", DEFAULT_META_MODEL),
            system_prompt=(
                "You are the Strategy agent. Synthesize the three supplied reports into a conservative "
                "research proposal. Return JSON with action BUY, SELL or HOLD, rationale, confidence 0..1, "
                "invalidation_conditions[]. If reports conflict, risk is unclear, or data is insufficient, HOLD. "
                "This is never an execution instruction."
            ),
            user_prompt=json.dumps({"market_intelligence": market, "technical_analysis": technical, "risk_assessment": risk}, default=str),
        )
        try:
            raw = response.strip()
            if raw.startswith("```json"):
                raw = raw.split("```json", 1)[1].split("```", 1)[0].strip()
            elif raw.startswith("```"):
                raw = raw.split("```", 1)[1].split("```", 1)[0].strip()
            return StrategyProposal.model_validate_json(raw)
        except Exception as exc:
            raise RuntimeError("Strategy agent returned an invalid proposal.") from exc
