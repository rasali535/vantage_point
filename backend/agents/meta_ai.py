"""Official Meta Model API client for Ras Ali AI Trader.

Uses Meta's OpenAI-compatible Chat Completions endpoint. The API key is
server-side only and is never exposed to the frontend.
"""
import hashlib
import logging
import os

import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

DEFAULT_META_MODEL = "muse-spark-1.3"


class MetaAIClient:
    def __init__(self):
        self.api_key = os.getenv("MODEL_API_KEY")
        self.base_url = os.getenv("META_MODEL_API_BASE_URL", "https://api.meta.ai/v1").rstrip("/")

        # A short one-way fingerprint lets operators compare the key loaded by
        # this process with their local key without ever logging the secret.
        key_fingerprint = (
            hashlib.sha256(self.api_key.encode("utf-8")).hexdigest()[:16]
            if self.api_key
            else "missing"
        )
        logger.info(
            "meta_model_api_runtime_config key_configured=%s key_fingerprint=%s "
            "base_url=%s default_model=%s",
            bool(self.api_key),
            key_fingerprint,
            self.base_url,
            DEFAULT_META_MODEL,
        )

    async def chat(self, model: str, system_prompt: str, user_prompt: str) -> str:
        if not self.api_key:
            raise RuntimeError("MODEL_API_KEY is not configured.")

        selected_model = model or DEFAULT_META_MODEL
        payload = {
            "model": selected_model,
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
        except httpx.HTTPStatusError as exc:
            # Meta's error envelope is useful for diagnosing route, model, and
            # project-access failures. Log only its structured error fields;
            # never log request headers, prompts, or credentials.
            error_code = None
            error_type = None
            error_message = None
            try:
                body = exc.response.json()
                error = body.get("error", {}) if isinstance(body, dict) else {}
                if isinstance(error, dict):
                    error_code = error.get("code")
                    error_type = error.get("type")
                    error_message = error.get("message")
            except (ValueError, TypeError):
                pass

            logger.error(
                "meta_model_api_http_error status=%s model=%s base_url=%s "
                "error_code=%s error_type=%s error_message=%s",
                exc.response.status_code,
                selected_model,
                self.base_url,
                str(error_code)[:120] if error_code is not None else None,
                str(error_type)[:120] if error_type is not None else None,
                str(error_message)[:500] if error_message is not None else None,
            )
            raise RuntimeError("Meta Model API request failed or returned an invalid response.") from exc
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as exc:
            logger.error(
                "meta_model_api_response_error error_type=%s model=%s base_url=%s",
                type(exc).__name__,
                selected_model,
                self.base_url,
            )
            raise RuntimeError("Meta Model API request failed or returned an invalid response.") from exc

        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("Meta Model API returned an empty response.")
        return content.strip()


meta_ai = MetaAIClient()
