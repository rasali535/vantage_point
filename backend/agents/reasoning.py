import os
import json
import asyncio
from typing import Dict, List
from agents.featherless import featherless
from dotenv import load_dotenv

load_dotenv()

class BoardroomCouncil:
    def __init__(self):
        self.research_model = os.getenv("RESEARCH_MODEL", "Qwen/Qwen2.5-72B-Instruct")
        self.trading_model = os.getenv("TRADING_MODEL", "deepseek-ai/DeepSeek-V3")
        # Use the trading model or fallback for the CEO role
        self.ceo_model = self.trading_model

    async def get_gc_opinion(self, market_data: str) -> str:
        """General Counsel: DeepSeek-V3 specializes in risk and logical audit."""
        return await featherless.chat(
            model=self.trading_model,
            system_prompt="You are the General Counsel of Vantage-Point. Audit this market state for compliance and hidden risk.",
            user_prompt=f"Market data: {market_data}"
        )

    async def get_macro_opinion(self, ticker: Dict) -> str:
        """Macro Strategist: Qwen 2.5-72B specializes in global trends and volatility."""
        return await featherless.chat(
            model=self.research_model,
            system_prompt="You are the Macro Strategist. Analyze the global trends and volatility for this asset.",
            user_prompt=f"Ticker: {json.dumps(ticker)}"
        )

    async def deliberate(self, ticker: Dict, ohlc: List, pair: str) -> Dict:
        """The Boardroom Council Deliberation Workflow via Featherless"""
        market_summary = f"Pair: {pair}, Last: {ticker.get('last')}, 24h Change: {ticker.get('change_percent')}%"
        
        # 1. Parallel Research (Featherless)
        gc_task = self.get_gc_opinion(market_summary)
        macro_task = self.get_macro_opinion(ticker)
        
        gc_view, macro_view = await asyncio.gather(gc_task, macro_task)
        
        # 2. Final CEO Decision (Featherless / Gemini)
        prompt = f"""
        BOARDROOM DELIBERATION for {pair}
        
        [General Counsel Opinion]: {gc_view}
        [Macro Strategist Opinion]: {macro_view}
        [Market Data]: {json.dumps(ohlc[:5])}
        
        As CEO, synthesize these views and make a final trade decision.
        Return ONLY valid JSON:
        {{
            "action": "BUY" | "SELL" | "HOLD",
            "reasoning": "A concise synthesis of the boardroom's debate",
            "risk_score": 0-100,
            "confidence": 0-1.0
        }}
        """
        
        # Pulling Gemini 1.5 through the Featherless endpoint
        response_text = await featherless.chat(
            model=self.ceo_model,
            system_prompt="You are the CEO of Vantage-Point Treasury.",
            user_prompt=prompt
        )
        
        # Clean up JSON formatting
        raw_text = response_text.strip()
        if "```json" in raw_text:
            raw_text = raw_text.split("```json")[1].split("```")[0].strip()
            
        try:
            return json.loads(raw_text)
        except:
            # Fallback for parsing errors
            return {
                "action": "HOLD",
                "reasoning": "Synthesis failed, defaulting to neutral state for safety.",
                "risk_score": 50,
                "confidence": 0.5
            }

boardroom = BoardroomCouncil()
