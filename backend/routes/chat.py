import logging
import os
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agents.meta_ai import (
    DEFAULT_META_MODEL,
    MetaAIAuthenticationError,
    MetaAIConfigError,
    MetaAIError,
    MetaAIModelNotFoundError,
    MetaAITimeoutError,
    meta_ai,
)

logger = logging.getLogger(__name__)
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
    except (MetaAIModelNotFoundError, MetaAIAuthenticationError, MetaAIConfigError) as exc:
        logger.warning("chat_meta_provider_rejected error=%s", exc.message)
        raise HTTPException(
            status_code=503,
            detail=f"AI assistant is unavailable: {exc.message} No trading action was taken.",
        ) from exc
    except MetaAITimeoutError as exc:
        logger.warning("chat_meta_provider_timeout error=%s", exc.message)
        raise HTTPException(
            status_code=504,
            detail="AI assistant request timed out. No trading action was taken.",
        ) from exc
    except MetaAIError as exc:
        logger.warning("chat_meta_provider_failed error=%s", exc.message)
        raise HTTPException(
            status_code=503,
            detail=f"AI assistant is temporarily unavailable ({exc.error_code or 'provider_error'}). No trading action was taken.",
        ) from exc
    except Exception as exc:
        logger.exception("chat_endpoint_failed error_type=%s", type(exc).__name__)
        raise HTTPException(
            status_code=503,
            detail="AI assistant is temporarily unavailable. No trading action was taken.",
        ) from exc
