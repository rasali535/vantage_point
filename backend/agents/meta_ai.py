"""Official Meta Model API client for Ras Ali AI Trader.

Uses Meta's OpenAI-compatible Chat Completions endpoint. The API key is
server-side only and is never exposed to the frontend.
"""
import asyncio
import hashlib
import logging
import os
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

DEFAULT_META_MODEL = "muse-spark-1.3"


class MetaAIError(RuntimeError):
    """Base exception for all Meta Model API failures."""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        status_code: Optional[int] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code


class MetaAIConfigError(MetaAIError):
    """Configuration error, such as missing credentials."""


class MetaAIAuthenticationError(MetaAIError):
    """Authentication failed (HTTP 401 / invalid API key)."""


class MetaAIModelNotFoundError(MetaAIError):
    """Requested model not found or inaccessible for key/account (HTTP 404)."""


class MetaAITimeoutError(MetaAIError):
    """Network timeout contacting the Meta Model API."""


class MetaAIResponseError(MetaAIError):
    """Invalid or malformed response returned by Meta Model API."""


def normalize_meta_base_url(url: Optional[str]) -> str:
    """Normalize base URL ensuring standard versioned endpoint root (https://api.meta.ai/v1)."""
    if not url or not url.strip():
        return "https://api.meta.ai/v1"
    raw = url.strip().rstrip("/")
    # Strip endpoints if accidentally provided in configuration
    for suffix in ("/chat/completions", "/chat", "/models", "/responses", "/messages"):
        if raw.endswith(suffix):
            raw = raw[:-len(suffix)].rstrip("/")
    if not raw.endswith("/v1"):
        raw = f"{raw}/v1"
    return raw


def parse_model_catalog(body: Any) -> List[str]:
    """Safely extract unique model IDs from documented and alternative catalog structures."""
    extracted: List[str] = []

    def _add_item(item: Any) -> None:
        if isinstance(item, str) and item.strip():
            extracted.append(item.strip())
        elif isinstance(item, dict):
            m_id = item.get("id") or item.get("name") or item.get("model")
            if isinstance(m_id, str) and m_id.strip():
                extracted.append(m_id.strip())

    if isinstance(body, dict):
        # Format 1 (OpenAI/Meta standard): {"object": "list", "data": [...]}
        data = body.get("data")
        if isinstance(data, list):
            for item in data:
                _add_item(item)
        elif isinstance(data, dict):
            sub_models = data.get("models") or data.get("items")
            if isinstance(sub_models, list):
                for item in sub_models:
                    _add_item(item)
            else:
                _add_item(data)

        # Format 2: {"models": [...]} or {"items": [...]}
        if not extracted:
            for alt_key in ("models", "items", "result"):
                alt_list = body.get(alt_key)
                if isinstance(alt_list, list):
                    for item in alt_list:
                        _add_item(item)
                    if extracted:
                        break

        # Format 3 (Single model object): {"id": "...", "object": "model"}
        if not extracted and ("id" in body or "object" in body):
            _add_item(body)

    elif isinstance(body, list):
        # Format 4 (Top-level array): [{"id": "muse-spark-1.3"}, ...] or ["muse-spark-1.3", ...]
        for item in body:
            _add_item(item)

    # Deduplicate while preserving discovery order
    return list(dict.fromkeys(extracted))


class MetaAIClient:
    def __init__(self):
        raw_key = os.getenv("MODEL_API_KEY")
        self.api_key = raw_key.strip() if raw_key else None
        self.base_url = normalize_meta_base_url(os.getenv("META_MODEL_API_BASE_URL"))
        self._lock = asyncio.Lock()
        self._catalog_cache: Optional[List[str]] = None
        self._catalog_checked = False

        # One-way fingerprint lets operators compare keys without ever logging secrets
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

    def _refresh_credentials(self) -> None:
        """Re-read env-derived config so a key added after import takes effect.

        The module-level ``meta_ai`` singleton is created at import time; without
        this refresh, a ``MODEL_API_KEY`` set after the first import would never
        be picked up until a process restart.
        """
        raw_key = os.getenv("MODEL_API_KEY")
        self.api_key = raw_key.strip() if raw_key and raw_key.strip() else None
        self.base_url = normalize_meta_base_url(os.getenv("META_MODEL_API_BASE_URL"))

    def _headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "RasAliAITrader/0.2.0 (MetaAIClient)",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    @staticmethod
    def _extract_error(response: httpx.Response) -> Dict[str, Any]:
        """Safely extract error fields without logging sensitive request headers or bodies."""
        try:
            body = response.json()
            if isinstance(body, dict):
                error = body.get("error")
                if isinstance(error, dict):
                    return {
                        "code": str(error.get("code") or "")[:120] or None,
                        "type": str(error.get("type") or "")[:120] or None,
                        "message": str(error.get("message") or "")[:500] or None,
                    }
                elif isinstance(error, str):
                    return {"message": error[:500]}
                detail = body.get("detail") or body.get("title")
                if detail:
                    return {"message": str(detail)[:500]}
        except Exception:
            pass
        return {"message": f"HTTP {response.status_code}"}

    async def discover_models(self, force_refresh: bool = False) -> List[str]:
        """Discover and cache available models from Meta API in a concurrency-safe manner."""
        self._refresh_credentials()
        if not self.api_key:
            raise MetaAIConfigError("MODEL_API_KEY is not configured.")

        if self._catalog_checked and not force_refresh and self._catalog_cache is not None:
            return self._catalog_cache

        async with self._lock:
            # Recheck inside lock
            if self._catalog_checked and not force_refresh and self._catalog_cache is not None:
                return self._catalog_cache

            try:
                async with httpx.AsyncClient(timeout=httpx.Timeout(8.0, connect=5.0)) as client:
                    response = await client.get(
                        f"{self.base_url}/models",
                        headers=self._headers(),
                    )

                if response.is_success:
                    body = response.json()
                    model_ids = parse_model_catalog(body)
                    self._catalog_cache = model_ids
                    self._catalog_checked = True

                    # Safe operational observability
                    keys_summary = (
                        ",".join(list(body.keys())[:10])
                        if isinstance(body, dict)
                        else type(body).__name__
                    )
                    logger.info(
                        "meta_model_catalog_discovered status=%s model_count=%d "
                        "structure_keys=%s sample=%s",
                        response.status_code,
                        len(model_ids),
                        keys_summary,
                        ",".join(model_ids[:5]),
                    )
                    return model_ids
                else:
                    self._catalog_checked = True
                    self._catalog_cache = []
                    err_info = self._extract_error(response)
                    logger.warning(
                        "meta_model_catalog_unavailable status=%s code=%s type=%s message=%s",
                        response.status_code,
                        err_info.get("code"),
                        err_info.get("type"),
                        err_info.get("message"),
                    )
                    if response.status_code == 401:
                        raise MetaAIAuthenticationError(
                            "Meta Model API authentication failed during catalog discovery.",
                            error_code=err_info.get("code") or "invalid_api_key",
                            status_code=401,
                        )
                    return []
            except httpx.TimeoutException as exc:
                logger.warning("meta_model_catalog_timeout error=%s", type(exc).__name__)
                return self._catalog_cache or []
            except MetaAIError:
                raise
            except Exception as exc:
                logger.warning("meta_model_catalog_failed error=%s", type(exc).__name__)
                return self._catalog_cache or []

    async def chat(self, model: str, system_prompt: str, user_prompt: str) -> str:
        """Call Meta's OpenAI-compatible Chat Completions endpoint."""
        self._refresh_credentials()
        if not self.api_key:
            raise MetaAIConfigError("MODEL_API_KEY is not configured.")

        selected_model = (model or DEFAULT_META_MODEL).strip()

        # Concurrency-safe catalog discovery
        try:
            discovered = await self.discover_models()
            if discovered and selected_model not in discovered:
                logger.warning(
                    "meta_target_model_not_in_catalog target=%s available_count=%d sample=%s",
                    selected_model,
                    len(discovered),
                    ",".join(discovered[:5]),
                )
        except MetaAIAuthenticationError:
            raise
        except Exception:
            # If discovery fails or is unreachable, proceed to chat completion
            # rather than failing prematurely on probe issues.
            pass

        payload = {
            "model": selected_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_completion_tokens": 1200,
        }

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=8.0)) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._headers(),
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as exc:
            err = self._extract_error(exc.response)
            err_code = err.get("code")
            err_type = err.get("type")
            err_msg = err.get("message")

            logger.error(
                "meta_model_api_http_error status=%s model=%s base_url=%s "
                "error_code=%s error_type=%s error_message=%s",
                exc.response.status_code,
                selected_model,
                self.base_url,
                err_code,
                err_type,
                err_msg,
            )

            if exc.response.status_code == 404 or err_code == "model_not_found":
                msg = (
                    f"Meta model '{selected_model}' was not found or is inaccessible "
                    "with configured credentials."
                )
                raise MetaAIModelNotFoundError(
                    msg, error_code="model_not_found", status_code=404
                ) from exc
            elif exc.response.status_code == 401 or err_code == "invalid_api_key":
                msg = "Meta Model API authentication failed. Verify MODEL_API_KEY."
                raise MetaAIAuthenticationError(
                    msg, error_code="invalid_api_key", status_code=401
                ) from exc
            else:
                msg = (
                    f"Meta Model API request failed (HTTP {exc.response.status_code}): "
                    f"{err_msg or 'upstream error'}"
                )
                raise MetaAIError(
                    msg, error_code=err_code, status_code=exc.response.status_code
                ) from exc

        except httpx.TimeoutException as exc:
            logger.error(
                "meta_model_api_timeout model=%s base_url=%s",
                selected_model,
                self.base_url,
            )
            raise MetaAITimeoutError(
                f"Meta Model API request timed out for model '{selected_model}'.",
                error_code="timeout",
            ) from exc

        except (ValueError, KeyError, IndexError, TypeError) as exc:
            logger.error(
                "meta_model_api_response_error error_type=%s model=%s base_url=%s",
                type(exc).__name__,
                selected_model,
                self.base_url,
            )
            raise MetaAIResponseError(
                f"Meta Model API returned an unexpected response format: {type(exc).__name__}",
                error_code="invalid_response",
            ) from exc

        except httpx.HTTPError as exc:
            logger.error(
                "meta_model_api_network_error error_type=%s model=%s base_url=%s",
                type(exc).__name__,
                selected_model,
                self.base_url,
            )
            raise MetaAIError(
                f"Meta Model API network connection failed: {type(exc).__name__}",
                error_code="network_error",
            ) from exc

        if not isinstance(content, str) or not content.strip():
            raise MetaAIResponseError(
                f"Meta Model API returned empty content for model '{selected_model}'.",
                error_code="empty_response",
            )
        return content.strip()

    async def check_readiness(self) -> Dict[str, Any]:
        """Report operational readiness of Meta Model API without exposing secrets."""
        self._refresh_credentials()
        key_fp = (
            hashlib.sha256(self.api_key.encode("utf-8")).hexdigest()[:16]
            if self.api_key
            else "missing"
        )
        if not self.api_key:
            return {
                "status": "not_configured",
                "configured": False,
                "key_fingerprint": "missing",
                "base_url": self.base_url,
                "default_model": DEFAULT_META_MODEL,
                "detail": "MODEL_API_KEY is not set.",
            }

        try:
            discovered = await self.discover_models()
            target_found = DEFAULT_META_MODEL in discovered
            return {
                "status": "ready" if (target_found or len(discovered) > 0) else "catalog_empty",
                "configured": True,
                "key_fingerprint": key_fp,
                "base_url": self.base_url,
                "default_model": DEFAULT_META_MODEL,
                "model_count": len(discovered),
                "default_model_available": target_found,
            }
        except MetaAIAuthenticationError:
            return {
                "status": "authentication_failed",
                "configured": True,
                "key_fingerprint": key_fp,
                "base_url": self.base_url,
                "default_model": DEFAULT_META_MODEL,
                "detail": "Invalid credentials or unauthorized.",
            }
        except Exception as exc:
            return {
                "status": "unreachable",
                "configured": True,
                "key_fingerprint": key_fp,
                "base_url": self.base_url,
                "default_model": DEFAULT_META_MODEL,
                "detail": type(exc).__name__,
            }


meta_ai = MetaAIClient()
