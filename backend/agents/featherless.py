import os
import json
import httpx
from typing import Dict, List
from dotenv import load_dotenv

load_dotenv()

class FeatherlessAgent:
    def __init__(self):
        self.api_key = os.getenv("FEATHERLESS_API_KEY")
        if not self.api_key or "rc_" not in self.api_key:
            print("⚠️ FEATHERLESS_API_KEY missing or invalid.")
        self.base_url = "https://api.featherless.ai/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    async def chat(self, model: str, system_prompt: str, user_prompt: str) -> str:
        if not self.api_key or "rc_" not in self.api_key:
            return "Consensus: Strategy maintains current trajectory. (Key missing)"
        """Calls the Featherless API using the OpenAI-compatible endpoint."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 1000
            }
            
            try:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
            except Exception as e:
                print(f"Featherless Error ({model}): {e}")
                return f"Error: {str(e)}"

featherless = FeatherlessAgent()
