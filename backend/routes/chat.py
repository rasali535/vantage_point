from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
from agents.reasoning import ReasoningAgent
import os

router = APIRouter()
reasoning_agent = ReasoningAgent()

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
        # We can use the last message as the primary query
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
        
        # Combine messages for context
        full_prompt = system_prompt + "\n\nUser History:\n"
        for msg in request.messages[:-1]:
            full_prompt += f"{msg.role.capitalize()}: {msg.content}\n"
        
        full_prompt += f"\nUser Query: {user_query}"
        
        # Call the reasoning agent
        # We'll use the raw analysis method or a new one
        # For now, let's just use the analyze_multimodal but we'll ignore the JSON extraction for chat
        # Actually, let's add a raw chat method to ReasoningAgent
        
        if hasattr(reasoning_agent, 'featherless_client'):
            # Use OpenAI SDK directly for chat
            response = reasoning_agent.featherless_client.chat.completions.create(
                model="meta-llama/Meta-Llama-3.1-70B-Instruct",
                messages=[
                    {"role": "system", "content": system_prompt},
                    *[{"role": m.role, "content": m.content} for m in request.messages]
                ],
                temperature=0.7
            )
            reply = response.choices[0].message.content
        else:
            # Fallback to Gemini if configured, or mock
            reply = "I'm currently in mock mode. DeepMind just released Gemini 1.5 Pro, and market sentiment is bullish on tech stocks!"
            
        return {"reply": reply}
        
    except Exception as e:
        print(f"Chat Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
