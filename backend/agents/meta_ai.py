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

# Preferred chat-capable Muse models, newest first. Used only when the
# configured model is absent from the key's discovered catalog.
META_CHAT_MODEL_FALLBACKS = (
    "muse-spark-1.3",
    "muse-spark-1.2",
    "muse-spark-1.1",
    "muse-spark-1.3-contributor",
    "muse-spark-1.2-contributor",
)

# Catalog entries with these prefixes can serve Chat Completions. Other
# families (image, voice, segmentation) cannot and are never substituted.
_CHAT_MODEL_FAMILIES = ("muse-spark", "muse-wonder", "muse-ember")


def meta_http_transport() -> httpx.AsyncHTTPTransport:
    """Build the HTTP transport for Meta API calls, pinned to IPv4 egress.

    Experiment: Render resolves both A and AAAA records for api.meta.ai, and
    byte-identical requests succeed from IPv4-only networks while
    Render-sourced calls receive empty catalogs and model_not_found. Until
    Meta confirms the cause, route around a potentially degraded IPv6 edge.
    """
    return httpx.AsyncHTTPTransport(local_address="0.0.0.0")


def normalize_model_id(model: Optional[str]) -> str:
    """Normalize a configured model ID to the bare Meta Model API ID.

    Operators sometimes configure provider-prefixed values
    (``meta/muse-spark-1.3``, as used by third-party routers). The Meta Model
    API expects the bare ID, so strip any provider prefix and whitespace.
    """
    raw = (model or "").strip()
    if "/" in raw:
        raw = raw.rsplit("/", 1)[-1].strip()
    return raw or DEFAULT_META_MODEL


def resolve_available_model(target: str, catalog: List[str]) -> str:
    """Pick the best usable chat model given the discovered catalog.

    Returns the catalog's own form of the ID so router-style catalogs keep
    working. Falls back through known Muse chat models, then any chat-family
    catalog entry. Returns the normalized target when the catalog is empty or
    holds no chat-capable model, letting the API return the authoritative error.
    """
    target_norm = normalize_model_id(target)
    if not catalog:
        return target_norm
    by_norm: Dict[str, str] = {}
    for entry in catalog:
        if not isinstance(entry, str) or not entry.strip():
            continue
        by_norm.setdefault(normalize_model_id(entry), entry.strip())
    if target_norm in by_norm:
        return by_norm[target_norm]
    for fallback in META_CHAT_MODEL_FALLBACKS:
        if fallback in by_norm:
            return by_norm[fallback]
    for norm, original in by_norm.items():
        if norm.startswith(_CHAT_MODEL_FAMILIES):
            return original
    return target_norm


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
        # Last /models attempt detail (status codes and shapes only, never secrets)
        # so the readiness endpoint can explain an empty catalog without log access.
        self._last_catalog_diagnostic: Optional[Dict[str, Any]] = None

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
                async with httpx.AsyncClient(timeout=httpx.Timeout(8.0, connect=5.0), transport=meta_http_transport()) as client:
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
                    self._last_catalog_diagnostic = {
                        "http_status": response.status_code,
                        "structure": keys_summary,
                        "model_count": len(model_ids),
                    }
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
                    self._last_catalog_diagnostic = {
                        "http_status": response.status_code,
                        "code": err_info.get("code"),
                        "type": err_info.get("type"),
                        "message": err_info.get("message"),
                    }
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
                self._last_catalog_diagnostic = {
                    "error": "timeout",
                    "detail": type(exc).__name__,
                }
                return self._catalog_cache or []
            except MetaAIError:
                raise
            except Exception as exc:
                logger.warning("meta_model_catalog_failed error=%s", type(exc).__name__)
                self._last_catalog_diagnostic = {
                    "error": "discovery_failed",
                    "detail": type(exc).__name__,
                }
                return self._catalog_cache or []

    def _model_not_found_message(self, requested: str, catalog: List[str]) -> str:
        """Build an actionable model-not-found message without secrets."""
        msg = (
            f"Meta model '{requested}' was not found or is inaccessible "
            "with configured credentials."
        )
        if catalog:
            msg += (
                f" Models available to this key ({len(catalog)}): "
                f"{', '.join(catalog[:8])}."
            )
        else:
            msg += (
                " The model catalog for this key is empty or unavailable; "
                "verify MODEL_API_KEY and model access."
            )
        return msg

    @staticmethod
    def _mentions_model(message: Optional[str], model: str) -> bool:
        text = (message or "").lower()
        return "model" in text or bool(model) and model.lower() in text

    async def chat(self, model: str, system_prompt: str, user_prompt: str) -> str:
        """Call Meta's OpenAI-compatible Chat Completions endpoint."""
        self._refresh_credentials()
        if not self.api_key:
            raise MetaAIConfigError("MODEL_API_KEY is not configured.")

        selected_model = normalize_model_id(model)

        # Concurrency-safe catalog discovery
        try:
            discovered = await self.discover_models()
        except MetaAIAuthenticationError:
            raise
        except Exception:
            # If discovery fails or is unreachable, proceed to chat completion
            # rather than failing prematurely on probe issues.
            discovered = []

        resolved_model = resolve_available_model(selected_model, discovered)
        if normalize_model_id(resolved_model) != selected_model:
            logger.warning(
                "meta_model_fallback target=%s resolved=%s available_count=%d sample=%s",
                selected_model,
                resolved_model,
                len(discovered),
                ",".join(discovered[:5]),
            )

        try:
            return await self._post_chat(
                resolved_model, system_prompt, user_prompt, discovered
            )
        except MetaAIModelNotFoundError as first_not_found:
            # The catalog may have been stale or empty at discovery time.
            # Refresh once and retry with a different catalog model if one exists.
            try:
                fresh = await self.discover_models(force_refresh=True)
            except Exception:
                raise first_not_found
            candidates = [
                entry
                for entry in fresh
                if normalize_model_id(entry) != normalize_model_id(resolved_model)
            ]
            retry_model = resolve_available_model(selected_model, candidates)
            if normalize_model_id(retry_model) == normalize_model_id(resolved_model):
                raise MetaAIModelNotFoundError(
                    self._model_not_found_message(selected_model, fresh),
                    error_code="model_not_found",
                    status_code=404,
                ) from first_not_found
            logger.warning(
                "meta_model_retry_after_not_found failed=%s retry=%s",
                resolved_model,
                retry_model,
            )
            return await self._post_chat(retry_model, system_prompt, user_prompt, fresh)

    async def _post_chat(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        catalog: List[str],
    ) -> str:
        """POST one Chat Completions request and map failures to typed errors."""
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_completion_tokens": 1200,
        }

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=8.0), transport=meta_http_transport()) as client:
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
                model,
                self.base_url,
                err_code,
                err_type,
                err_msg,
            )

            if err_code == "model_not_found" or (
                exc.response.status_code == 404
                and self._mentions_model(err_msg, model)
            ):
                raise MetaAIModelNotFoundError(
                    self._model_not_found_message(
                        normalize_model_id(model), catalog
                    ),
                    error_code="model_not_found",
                    status_code=404,
                ) from exc
            elif exc.response.status_code == 404:
                raise MetaAIError(
                    "Meta Model API endpoint not found (HTTP 404) at "
                    f"{self.base_url}/chat/completions. "
                    "Verify META_MODEL_API_BASE_URL.",
                    error_code="endpoint_not_found",
                    status_code=404,
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
                model,
                self.base_url,
            )
            raise MetaAITimeoutError(
                f"Meta Model API request timed out for model '{model}'.",
                error_code="timeout",
            ) from exc

        except (ValueError, KeyError, IndexError, TypeError) as exc:
            logger.error(
                "meta_model_api_response_error error_type=%s model=%s base_url=%s",
                type(exc).__name__,
                model,
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
                model,
                self.base_url,
            )
            raise MetaAIError(
                f"Meta Model API network connection failed: {type(exc).__name__}",
                error_code="network_error",
            ) from exc

        if not isinstance(content, str) or not content.strip():
            raise MetaAIResponseError(
                f"Meta Model API returned empty content for model '{model}'.",
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
            normalized = [normalize_model_id(entry) for entry in discovered]
            target_found = normalize_model_id(DEFAULT_META_MODEL) in normalized
            return {
                "status": "ready" if (target_found or len(discovered) > 0) else "catalog_empty",
                "configured": True,
                "key_fingerprint": key_fp,
                "base_url": self.base_url,
                "default_model": DEFAULT_META_MODEL,
                "model_count": len(discovered),
                "default_model_available": target_found,
                "models_sample": discovered[:8],
                "catalog_diagnostic": self._last_catalog_diagnostic or {},
            }
        except MetaAIAuthenticationError:
            return {
                "status": "authentication_failed",
                "configured": True,
                "key_fingerprint": key_fp,
                "base_url": self.base_url,
                "default_model": DEFAULT_META_MODEL,
                "detail": "Invalid credentials or unauthorized.",
                "catalog_diagnostic": self._last_catalog_diagnostic or {},
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
