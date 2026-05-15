import os
import json
import asyncio
from typing import Dict, List
import google.generativeai as genai
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

class BoardroomCouncil:
    def __init__(self):
        # We use Gemini 1.5 Pro as the CEO (Orchestrator)
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.ceo_model = genai.GenerativeModel('gemini-1.5-pro')
        
        # We use Claude 3.5 Sonnet as the General Counsel (Audit/Risk)
        self.anthropic = Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))

    async def get_gc_opinion(self, market_data: str) -> str:
        """General Counsel: Claude 3.5 Sonnet specializes in compliance and risk mitigation."""
        response = self.anthropic.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=300,
            system="You are the General Counsel of Vantage-Point Treasury. Your role is to identify regulatory risks and hidden contract hazards in trade decisions.",
            messages=[{"role": "user", "content": f"Audit this market state for risk: {market_data}"}]
        )
        return response.content[0].text

    async def get_macro_opinion(self, ticker: Dict) -> str:
        """Macro Strategist: Specialized in global trends (Simulated Qwen/Llama)."""
        # Placeholder for external model call (e.g. OpenRouter/Qwen)
        return f"Macro analysis shows bullish momentum on tech equities. Ticker last: {ticker.get('last')}. Volatility is stabilizing."

    async def deliberate(self, ticker: Dict, ohlc: List, pair: str) -> Dict:
        """The Boardroom Council Deliberation Workflow"""
        market_summary = f"Pair: {pair}, Last: {ticker.get('last')}, 24h Change: {ticker.get('change_percent')}%"
        
        # 1. Parallel Research
        gc_task = self.get_gc_opinion(market_summary)
        macro_task = self.get_macro_opinion(ticker)
        
        gc_view, macro_view = await asyncio.gather(gc_task, macro_task)
        
        # 2. Final CEO Decision (Gemini)
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
        
        response = self.ceo_model.generate_content(prompt)
        raw_text = response.text.strip()
        if "```json" in raw_text:
            raw_text = raw_text.split("```json")[1].split("```")[0].strip()
            
        return json.loads(raw_text)

boardroom = BoardroomCouncil()
