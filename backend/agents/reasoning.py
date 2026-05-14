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
