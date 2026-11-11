import os

import httpx
from dotenv import load_dotenv

load_dotenv()


class FeatherlessAgent:
    """OpenAI-compatible Featherless client with fail-closed provider handling."""

    def __init__(self):
        self.api_key = os.getenv("FEATHERLESS_API_KEY")
        self.base_url = os.getenv("FEATHERLESS_BASE_URL", "https://api.featherless.ai/v1")

    async def chat(self, model: str, system_prompt: str, user_prompt: str) -> str:
        if not self.api_key:
            raise RuntimeError("FEATHERLESS_API_KEY is not configured.")

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 1200,
        }

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(20.0, connect=5.0)) as client:
                response = await client.post(
                    f"{self.base_url.rstrip('/')}/chat/completions",
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
            # Never substitute synthetic analysis when the model provider fails.
            raise RuntimeError("Featherless model request failed or returned an invalid response.") from exc

        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("Featherless returned an empty model response.")
        return content.strip()


featherless = FeatherlessAgent()
