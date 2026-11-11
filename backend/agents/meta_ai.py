"""Official Meta Model API client for Ras Ali AI Trader.

Uses Meta's OpenAI-compatible Chat Completions endpoint. The API key is
server-side only and is never exposed to the frontend.
"""
import os

import httpx
from dotenv import load_dotenv

load_dotenv()

DEFAULT_META_MODEL = "muse-spark-1.3"


class MetaAIClient:
    def __init__(self):
        self.api_key = os.getenv("MODEL_API_KEY")
        self.base_url = os.getenv("META_MODEL_API_BASE_URL", "https://api.meta.ai/v1").rstrip("/")

    async def chat(self, model: str, system_prompt: str, user_prompt: str) -> str:
        if not self.api_key:
            raise RuntimeError("MODEL_API_KEY is not configured.")

        payload = {
            "model": model or DEFAULT_META_MODEL,
            "messages": [
                {"role": "developer", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_completion_tokens": 1200,
        }

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=8.0)) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"]
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("Meta Model API request failed or returned an invalid response.") from exc

        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("Meta Model API returned an empty response.")
        return content.strip()


meta_ai = MetaAIClient()
