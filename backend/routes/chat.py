from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from agents.meta_ai import meta_ai, DEFAULT_META_MODEL
import os

router = APIRouter()


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    context: Optional[str] = ""


@router.post("/")
async def chat_with_agent(request: ChatRequest):
    if not request.messages:
        raise HTTPException(status_code=400, detail="At least one message is required.")

    user_query = request.messages[-1].content
    system_prompt = """
    You are the Ras Ali AI Trader research assistant.
    Help users understand crypto markets, trading concepts, risk controls,
    the Kraken-connected analysis workflow, and the application interface.
    Never claim that an order was placed, a balance was verified, or a market
    condition is current unless the application supplied verified data.
    Do not provide fabricated prices, portfolio figures, performance, or
    execution confirmations. Trading execution is disabled in this build.
    Be concise, transparent about uncertainty, and distinguish analysis from
    financial advice.
    """

    chat_model = os.getenv("RESEARCH_MODEL", DEFAULT_META_MODEL)
    try:
        reply = await meta_ai.chat(
            model=chat_model,
            system_prompt=system_prompt,
            user_prompt=user_query,
        )
        if not isinstance(reply, str) or reply.startswith("Error:") or "Key missing" in reply:
            raise RuntimeError("AI provider unavailable")
        return {"reply": reply}
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="AI assistant is temporarily unavailable. No trading action was taken.",
        ) from exc
