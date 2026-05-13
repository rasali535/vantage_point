import google.generativeai as genai
import os
import json
import httpx
from typing import Dict, List

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

class ReasoningAgent:
    def __init__(self, model_name="gemini-1.5-flash"):
        self.gemini_model = genai.GenerativeModel(model_name)
        self.featherless_api_key = os.getenv("FEATHERLESS_API_KEY")
        self.featherless_url = "https://api.featherless.ai/v1/chat/completions"

    async def _analyze_with_featherless(self, prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.featherless_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "meta-llama/Meta-Llama-3-70B-Instruct",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(self.featherless_url, headers=headers, json=payload, timeout=60.0)
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
            else:
                raise Exception(f"Featherless Error: {response.text}")

    async def analyze_meeting(self, transcript: str, context: str = "") -> Dict:
        prompt = f"""
        Analyze the following meeting transcript and context.
        Return ONLY a JSON object with:
        - "Key Decisions": list of strings
        - "Action Items": list of {{"task": string, "owner": string, "deadline": string}}
        - "Risks and Blockers": list of strings
        - "Overall Deal/Project Health": number 0-100
        - "Confidence Score": number 0.0-1.0
        
        Transcript:
        {transcript}
        
        Additional Context:
        {context}
        """

        try:
            if self.featherless_api_key:
                print("Using Featherless reasoning engine...")
                raw_response = await self._analyze_with_featherless(prompt)
            elif os.getenv("GEMINI_API_KEY"):
                print("Using Gemini reasoning engine...")
                response = self.gemini_model.generate_content(prompt)
                raw_response = response.text
            else:
                print("Using Mock reasoning engine...")
                return {
                    "Key Decisions": ["Agreed on 99.99% SLA for Acme Corp", "Budget check assigned to Ops"],
                    "Action Items": [
                        {"task": "Check budget for enterprise cluster", "owner": "Charlie", "deadline": "Friday"},
                        {"task": "Send follow-up SLA draft", "owner": "Alice", "deadline": "Friday"}
                    ],
                    "Risks and Blockers": ["Ops budget might exceed original quote"],
                    "Overall Deal/Project Health": 85,
                    "Confidence Score": 0.95
                }

            # Clean JSON response
            text = raw_response.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            
            return json.loads(text.strip())
        except Exception as e:
            print(f"Agent Error: {e}")
            return {
                "error": str(e),
                "Key Decisions": ["Extraction failed"],
                "Action Items": [],
                "Risks and Blockers": ["AI Processing Error"],
                "Overall Deal/Project Health": 50,
                "Confidence Score": 0.0
            }
