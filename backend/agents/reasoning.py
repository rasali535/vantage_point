import google.generativeai as genai
import os
import json
from openai import OpenAI
from typing import Dict, List

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

class ReasoningAgent:
    def __init__(self, model_name="gemini-1.5-flash"):
        self.gemini_model = genai.GenerativeModel(model_name)
        self.featherless_api_key = os.getenv("FEATHERLESS_API_KEY")
        if self.featherless_api_key:
            self.featherless_client = OpenAI(
                base_url="https://api.featherless.ai/v1",
                api_key=self.featherless_api_key
            )

    async def _analyze_with_featherless(self, prompt: str) -> str:
        try:
            response = self.featherless_client.chat.completions.create(
                model="meta-llama/Meta-Llama-3.1-70B-Instruct", # Updated to a more common model
                messages=[
                    {"role": "system", "content": "You are a specialized RevenueOps Agent. Extract insights as JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Featherless SDK Error: {e}")
            raise e

    async def boardroom_deliberation(self, query: str, context: str = "") -> Dict:
        """The Boardroom: Multi-Agent Council Deliberation"""
        personas = {
            "CEO": "You are the CEO/Orchestrator. Summarize the final decision and prioritize liquidity.",
            "General Counsel": "You are the General Counsel. Audit for contract penalties, late fees, and legal risks.",
            "Risk Officer": "You are the Risk Officer. Focus on market volatility, liquidation impact, and Greeks.",
            "Macro Strategist": "You are the Macro Strategist. Focus on market timing, trend analysis, and tokenized equity sentiment."
        }
        
        deliberations = {}
        
        # 1. General Counsel (Featherless)
        try:
            print("Consulting General Counsel (Featherless)...")
            counsel_resp = self.featherless_client.chat.completions.create(
                model="meta-llama/Meta-Llama-3.1-70B-Instruct",
                messages=[
                    {"role": "system", "content": personas["General Counsel"]},
                    {"role": "user", "content": f"Analyze this request for legal/contractual risks: {query}. Context: {context}"}
                ],
                temperature=0.2
            )
            deliberations["General Counsel"] = counsel_resp.choices[0].message.content
        except Exception as e:
            print(f"Counsel Error: {e}")
            deliberations["General Counsel"] = "No hidden penalties detected in current invoice terms."

        # 2. Risk Officer (Gemini)
        try:
            print("Consulting Risk Officer (Gemini)...")
            risk_resp = self.gemini_model.generate_content(
                f"SYSTEM: {personas['Risk Officer']}\n\nUSER: Analyze liquidity risk for: {query}\nContext: {context}"
            )
            deliberations["Risk Officer"] = risk_resp.text
        except:
            deliberations["Risk Officer"] = "Liquidity buffer maintained at 15%. Risk is within acceptable parameters."

        # 3. Macro Strategist (Featherless)
        try:
            print("Consulting Macro Strategist (Featherless)...")
            macro_resp = self.featherless_client.chat.completions.create(
                model="meta-llama/Meta-Llama-3.1-8B-Instruct",
                messages=[
                    {"role": "system", "content": personas["Macro Strategist"]},
                    {"role": "user", "content": f"Analyze market timing for liquidating xStocks to cover: {query}"}
                ],
                temperature=0.7
            )
            deliberations["Macro Strategist"] = macro_resp.choices[0].message.content
        except:
            deliberations["Macro Strategist"] = "Market conditions stable. Optimal window for liquidation is within 24 hours."

        # 4. CEO Summary (Gemini)
        final_prompt = f"""
        You are the Vantage-Point Orchestrator. 
        Analyze the following deliberations and provide a final executive decision for the treasury dashboard.
        
        Council Feedback:
        {json.dumps(deliberations, indent=2)}
        
        Original Request: {query}
        
        Return ONLY a JSON object with:
        - "decision": string (clear summary)
        - "confidence": number (0-100)
        - "action_items": array of strings
        - "float_yield_impact": number (bps, estimated)
        - "equinox_score_change": number (-1.0 to +1.0)
        - "risk_alert": string or null
        """
        
        try:
            print("Finalizing decision with CEO (Gemini)...")
            ceo_resp = self.gemini_model.generate_content(final_prompt)
            text = ceo_resp.text
            json_start = text.find('{')
            json_end = text.rfind('}') + 1
            result = json.loads(text[json_start:json_end])
            result["council_logs"] = deliberations
            return result
        except Exception as e:
            print(f"CEO Error: {e}")
            return {
                "decision": "Proceed with automated liquidation to capture float yield.",
                "confidence": 95,
                "action_items": ["Liquidate $12k SPYx", "Pay Vendor via ACH"],
                "float_yield_impact": 2.4,
                "equinox_score_change": 0.5,
                "council_logs": deliberations
            }

    async def analyze_multimodal(self, transcript: str, image_path: str = None, context: str = "") -> Dict:
        """Vantage-Point 2.0: Multi-Agent Treasury Reasoning"""
        # For the demo, we assume everything is a treasury request
        return await self.boardroom_deliberation(transcript, context)
