import google.generativeai as genai
import os
import json
from typing import Dict, List

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

class ReasoningAgent:
    def __init__(self, model_name="gemini-1.5-flash"):
        self.model = genai.GenerativeModel(model_name)

    async def analyze_meeting(self, transcript: str, context: str = "") -> Dict:
        if not os.getenv("GEMINI_API_KEY"):
            # Mock Analysis for demonstration
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
            response = self.model.generate_content(prompt)
            # Find JSON block
            text = response.text
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            
            return json.loads(text.strip())
        except Exception as e:
            print(f"Agent Error: {e}")
            return {
                "error": "Failed to parse agent response",
                "Key Decisions": ["Extraction failed"],
                "Action Items": [],
                "Risks and Blockers": ["AI Processing Error"],
                "Overall Deal/Project Health": 50,
                "Confidence Score": 0.0
            }
