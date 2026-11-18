"""Hugging Face Inference Providers client for optional research/chat assistance.

Model output is advisory only. Deterministic technical signals and the risk engine
remain authoritative for every paper-trading decision.
"""
import os
import httpx


DEFAULT_CHAT_MODEL = "Qwen/Qwen3-4B-Thinking-2507:cheapest"
DEFAULT_CHAT_URL = "https://router.huggingface.co/v1/chat/completions"


class HuggingFaceNotConfigured(RuntimeError):
    pass


class HuggingFaceClient:
    def __init__(self):
        self.token = os.getenv("HF_TOKEN", "").strip()
        self.model = os.getenv("HF_CHAT_MODEL", DEFAULT_CHAT_MODEL).strip()
        self.url = os.getenv("HF_CHAT_COMPLETIONS_URL", DEFAULT_CHAT_URL).strip()
        self.timeout = min(45.0, max(5.0, float(os.getenv("HF_REQUEST_TIMEOUT_SECONDS", "20"))))

    @property
    def configured(self) -> bool:
        return bool(self.token)

    async def chat(self, messages: list[dict], *, max_tokens: int = 500, temperature: float = 0.2) -> str:
        if not self.configured:
            raise HuggingFaceNotConfigured("Hugging Face is not configured. Set HF_TOKEN in the server environment.")
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max(1, min(int(max_tokens), 1200)),
            "temperature": max(0.0, min(float(temperature), 1.0)),
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                self.url,
                headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"},
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        choices = data.get("choices") or []
        content = ((choices[0].get("message") or {}).get("content") if choices else None)
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("Hugging Face returned an empty chat completion.")
        return content.strip()


huggingface_client = HuggingFaceClient()
