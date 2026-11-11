import os
import json
import asyncio
from typing import Dict, List
from agents.meta_ai import meta_ai, DEFAULT_META_MODEL
from dotenv import load_dotenv

load_dotenv()

DEFAULT_LLAMA_MODEL = DEFAULT_META_MODEL


class BoardroomCouncil:
    def __init__(self):
        self.research_model = os.getenv("RESEARCH_MODEL", DEFAULT_LLAMA_MODEL)
        self.risk_model = os.getenv("RISK_MODEL", DEFAULT_LLAMA_MODEL)
        self.trading_model = os.getenv("TRADING_MODEL", DEFAULT_LLAMA_MODEL)

    async def get_risk_opinion(self, market_data: str) -> str:
        return await meta_ai.chat(
            model=self.risk_model,
            system_prompt=(
                "You are the independent risk analyst for Ras Ali AI Trader. "
                "Assess market conditions, downside risk, liquidity and uncertainty. "
                "You cannot approve or submit orders; deterministic controls are authoritative."
            ),
            user_prompt=f"Market data: {market_data}",
        )

    async def get_market_opinion(self, ticker: Dict) -> str:
        return await meta_ai.chat(
            model=self.research_model,
            system_prompt=(
                "You are the market intelligence analyst for Ras Ali AI Trader. "
                "Analyse the supplied Kraken spot ticker only. Do not invent external events or prices."
            ),
            user_prompt=f"Verified Kraken ticker: {json.dumps(ticker)}",
        )

    async def deliberate(self, ticker: Dict, ohlc: List, pair: str, whipsaw_report: Dict = None) -> Dict:
        whipsaw_context = ""
        if whipsaw_report:
            whipsaw_context = f"""
[SIGNAL QUALITY AND DETERMINISTIC FILTER]:
- Kaufman Efficiency Ratio: {whipsaw_report.get('efficiency_ratio')} ({whipsaw_report.get('regime')})
- ATR: {whipsaw_report.get('atr')} ({whipsaw_report.get('pct_volatility')}% of price)
- Whipsaw risk: {whipsaw_report.get('whipsaw_risk')}
- Deterministic recommendation: {whipsaw_report.get('action_recommendation')}
- Filter details: {whipsaw_report.get('reason')}
"""

        market_summary = (
            f"Pair: {pair}; last: {ticker.get('last')}; "
            f"24-hour change: {ticker.get('change_percent')}%."
        )
        risk_task = self.get_risk_opinion(market_summary)
        market_task = self.get_market_opinion(ticker)
        risk_view, market_view = await asyncio.gather(risk_task, market_task)

        prompt = f"""
RAS ALI AI TRADER MARKET DECISION FOR {pair}

[Risk analyst]: {risk_view}
[Market intelligence]: {market_view}
{whipsaw_context}
[Verified Kraken OHLC sample]: {json.dumps(ohlc[-10:])}

Propose one action for a human-reviewed research workflow. This is not an
execution instruction. If market data is insufficient, risk is elevated, or
the deterministic recommendation is FORCE_HOLD or ADVISE_HOLD, choose HOLD.
Do not claim any trade has been placed.

Return ONLY valid JSON:
{{
  "action": "BUY" | "SELL" | "HOLD",
  "reasoning": "Explain the evidence and uncertainty briefly.",
  "risk_score": 0-100,
  "confidence": 0-1.0
}}
"""
        response_text = await meta_ai.chat(
            model=self.trading_model,
            system_prompt=(
                "You are the strategy synthesis analyst for Ras Ali AI Trader. "
                "Return a research recommendation only. You cannot execute trades."
            ),
            user_prompt=prompt,
        )

        raw_text = response_text.strip()
        if raw_text.startswith("```json"):
            raw_text = raw_text.split("```json", 1)[1].split("```", 1)[0].strip()
        elif raw_text.startswith("```"):
            raw_text = raw_text.split("```", 1)[1].split("```", 1)[0].strip()

        try:
            decision = json.loads(raw_text)
        except (json.JSONDecodeError, TypeError) as exc:
            raise RuntimeError("AI strategy response was not valid JSON.") from exc

        action = str(decision.get("action", "")).upper()
        if action not in {"BUY", "SELL", "HOLD"}:
            raise RuntimeError("AI strategy response contained an invalid action.")

        try:
            risk_score = float(decision["risk_score"])
            confidence = float(decision["confidence"])
        except (KeyError, TypeError, ValueError) as exc:
            raise RuntimeError("AI strategy response omitted valid risk or confidence values.") from exc

        if not 0 <= risk_score <= 100 or not 0 <= confidence <= 1:
            raise RuntimeError("AI strategy response contained out-of-range scores.")

        return {
            "action": action,
            "reasoning": str(decision.get("reasoning", "No reasoning supplied.")),
            "risk_score": risk_score,
            "confidence": confidence,
            "model": self.trading_model,
            "execution_status": "not_submitted",
        }


boardroom = BoardroomCouncil()
