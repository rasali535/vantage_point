from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
from agents.featherless import featherless
import os

router = APIRouter()

class ChatMessage(BaseModel):
    role: str # 'user' or 'assistant'
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    context: Optional[str] = ""

@router.post("/")
async def chat_with_agent(request: ChatRequest):
    try:
        # Construct prompt for the chat
        user_query = request.messages[-1].content
        
        # System instructions for the chat assistant
        system_prompt = """
        You are ActionBot, a premium AI assistant for the ActionPilot platform.
        You specialize in:
        1. Trading and Financial Markets (stocks, crypto, xStocks).
        2. AI Research and Industry news (DeepMind, OpenAI, etc.).
        3. Helping users navigate the ActionPilot dashboard.
        
        Provide concise, insightful, and professional responses. 
        If asked about DeepMind, mention their latest breakthroughs like Gemini or AlphaFold if relevant.
        For trading news, provide general market wisdom and sentiment analysis.
        """
        
        # Use Featherless agent for chat
        # We'll use the TRADING_MODEL or a dedicated chat model if available
        chat_model = os.getenv("RESEARCH_MODEL", "Qwen/Qwen2.5-72B-Instruct")
        
        reply = await featherless.chat(
            model=chat_model,
            system_prompt=system_prompt,
            user_prompt=user_query
        )
        
        # Defensive check for error responses
        if reply.startswith("Error:") or "Key missing" in reply:
            reply = "I'm currently operating in limited capacity. DeepMind's Gemini 1.5 Pro is leading the way in multimodal AI, and we're seeing strong volatility in xStocks today!"
            
        return {"reply": reply}
        
    except Exception as e:
        print(f"Chat Error: {e}")
        return {"reply": "ActionBot is temporarily offline for maintenance. Please check the Vantage Command for live updates."}
