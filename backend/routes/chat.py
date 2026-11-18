"""Chat endpoint is intentionally disabled while external inference is retired."""
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

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
    raise HTTPException(
        status_code=503,
        detail=(
            "The hosted AI chat assistant is temporarily disabled while external model "
            "inference is retired. Deterministic market analysis, risk controls and "
            "paper trading remain available."
        ),
    )
