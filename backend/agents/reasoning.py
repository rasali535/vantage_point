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

    async def analyze_multimodal(self, transcript: str, image_path: str = None, context: str = "") -> Dict:
        """Advanced Multimodal Reasoning using Gemini 1.5 Flash"""
        prompt = f"""
        You are a specialized RevenueOps Agent. 
        Analyze the following sales call transcript and any attached visual context (like CRM screenshots or contracts).
        
        Return ONLY a JSON object with:
        - "Deal Status Update": summary of current deal stage
        - "Visual Insights": insights extracted from the attached image (if any)
        - "Sales Objections": list of objections raised
        - "Action Items": list of {{"task": string, "owner": string, "deadline": string}}
        - "Risk Assessment": high-level risks
        - "Deal Health Score": number 0-100
        
        Transcript:
        {transcript}
        
        CRM Context:
        {context}
        """

        try:
            if image_path and os.path.exists(image_path):
                print(f"Using Gemini Multimodal reasoning for image: {image_path}")
                # Load image for Gemini
                with open(image_path, "rb") as f:
                    img_data = f.read()
                
                # Gemini Multimodal Call
                response = self.gemini_model.generate_content([
                    prompt,
                    {"mime_type": "image/jpeg", "data": img_data}
                ])
                raw_response = response.text
            elif self.featherless_api_key:
                print("Using Featherless reasoning engine...")
                raw_response = await self._analyze_with_featherless(prompt)
            elif os.getenv("GEMINI_API_KEY"):
                print("Using Gemini reasoning engine...")
                response = self.gemini_model.generate_content(prompt)
                raw_response = response.text
            else:
                print("Using Mock reasoning engine...")
                return {
                    "Deal Status Update": "Mock data: SLA agreed.",
                    "Sales Objections": ["Price too high"],
                    "Action Items": [{"task": "Follow up", "owner": "Alice", "deadline": "Friday"}],
                    "Risk Assessment": "Budget check pending",
                    "Deal Health Score": 85
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
