import asyncio
import os
import unittest
from unittest.mock import AsyncMock, patch

import httpx

from agents.meta_ai import (
    DEFAULT_META_MODEL,
    MetaAIAuthenticationError,
    MetaAIClient,
    MetaAIConfigError,
    MetaAIError,
    MetaAIModelNotFoundError,
    MetaAIResponseError,
    MetaAITimeoutError,
    normalize_meta_base_url,
    parse_model_catalog,
)


class MetaAICatalogParsingTests(unittest.TestCase):
    def test_standard_openai_meta_catalog_format(self):
        body = {
            "object": "list",
            "data": [
                {"id": "muse-spark-1.3", "object": "model", "created": 1711929600, "owned_by": "meta"},
                {"id": "muse-ember-1.0", "object": "model", "created": 1711929600, "owned_by": "meta"},
            ],
        }
        result = parse_model_catalog(body)
        self.assertEqual(result, ["muse-spark-1.3", "muse-ember-1.0"])

    def test_catalog_with_data_list_of_strings(self):
        body = {"data": ["muse-spark-1.3", "muse-wonder-1.0"]}
        result = parse_model_catalog(body)
        self.assertEqual(result, ["muse-spark-1.3", "muse-wonder-1.0"])

    def test_catalog_with_models_key(self):
        body = {"models": [{"id": "muse-spark-1.3"}, {"name": "muse-ember-1.0"}]}
        result = parse_model_catalog(body)
        self.assertEqual(result, ["muse-spark-1.3", "muse-ember-1.0"])

    def test_catalog_top_level_list_of_dicts(self):
        body = [{"id": "muse-spark-1.3"}, {"id": "muse-wonder-1.0"}]
        result = parse_model_catalog(body)
        self.assertEqual(result, ["muse-spark-1.3", "muse-wonder-1.0"])

    def test_catalog_top_level_list_of_strings(self):
        body = ["muse-spark-1.3", "muse-wonder-1.0"]
        result = parse_model_catalog(body)
        self.assertEqual(result, ["muse-spark-1.3", "muse-wonder-1.0"])

    def test_catalog_single_model_dict(self):
        body = {"id": "muse-spark-1.3", "object": "model"}
        result = parse_model_catalog(body)
        self.assertEqual(result, ["muse-spark-1.3"])

    def test_catalog_nested_data_models_dict(self):
        body = {"data": {"models": [{"id": "muse-spark-1.3"}]}}
        result = parse_model_catalog(body)
        self.assertEqual(result, ["muse-spark-1.3"])

    def test_unexpected_or_malformed_formats_do_not_crash(self):
        for malformed in [{}, None, [], "plain text", 123, {"data": None}, {"data": [None, 42, {}]}]:
            result = parse_model_catalog(malformed)
            self.assertEqual(result, [])


class MetaAIUrlNormalizationTests(unittest.TestCase):
    def test_missing_or_empty_url_defaults_to_v1(self):
        self.assertEqual(normalize_meta_base_url(None), "https://api.meta.ai/v1")
        self.assertEqual(normalize_meta_base_url(""), "https://api.meta.ai/v1")
        self.assertEqual(normalize_meta_base_url("   "), "https://api.meta.ai/v1")

    def test_url_without_v1_appends_v1(self):
        self.assertEqual(normalize_meta_base_url("https://api.meta.ai"), "https://api.meta.ai/v1")
        self.assertEqual(normalize_meta_base_url("https://api.meta.ai/"), "https://api.meta.ai/v1")

    def test_url_with_v1_preserved(self):
        self.assertEqual(normalize_meta_base_url("https://api.meta.ai/v1"), "https://api.meta.ai/v1")
        self.assertEqual(normalize_meta_base_url("https://api.meta.ai/v1/"), "https://api.meta.ai/v1")

    def test_url_with_trailing_chat_completions_stripped(self):
        self.assertEqual(
            normalize_meta_base_url("https://api.meta.ai/v1/chat/completions"),
            "https://api.meta.ai/v1",
        )
        self.assertEqual(
            normalize_meta_base_url("https://api.meta.ai/v1/models"),
            "https://api.meta.ai/v1",
        )


class MetaAIClientExecutionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.test_key = "LLM_test_key_12345"
        self.env_patch = patch.dict(os.environ, {"MODEL_API_KEY": self.test_key})
        self.env_patch.start()

    def tearDown(self):
        self.env_patch.stop()

    async def test_missing_api_key_raises_config_error(self):
        with patch.dict(os.environ, {"MODEL_API_KEY": ""}):
            client = MetaAIClient()
            with self.assertRaises(MetaAIConfigError):
                await client.chat("muse-spark-1.3", "system", "user")

    async def test_successful_chat_completion(self):
        client = MetaAIClient()

        # Mock GET /models discovery
        models_resp = httpx.Response(
            status_code=200,
            json={"object": "list", "data": [{"id": "muse-spark-1.3", "object": "model"}]},
            request=httpx.Request("GET", f"{client.base_url}/models"),
        )
        # Mock POST /chat/completions
        chat_resp = httpx.Response(
            status_code=200,
            json={
                "id": "chatcmpl-123",
                "object": "chat.completion",
                "model": "muse-spark-1.3",
                "choices": [{"message": {"role": "assistant", "content": "Analysis complete."}}],
            },
            request=httpx.Request("POST", f"{client.base_url}/chat/completions"),
        )

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get, \
             patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_get.return_value = models_resp
            mock_post.return_value = chat_resp

            result = await client.chat("muse-spark-1.3", "system prompt", "user query")
            self.assertEqual(result, "Analysis complete.")
            mock_post.assert_called_once()
            call_kwargs = mock_post.call_args[1]
            self.assertEqual(call_kwargs["json"]["model"], "muse-spark-1.3")
            self.assertIn("Authorization", call_kwargs["headers"])
            self.assertTrue(call_kwargs["headers"]["Authorization"].startswith("Bearer LLM_"))

    async def test_model_not_found_raises_structured_error(self):
        client = MetaAIClient()

        error_body = {
            "error": {
                "code": "model_not_found",
                "type": "invalid_request_error",
                "message": "The requested model was not found.",
            }
        }
        mock_response = httpx.Response(
            status_code=404,
            json=error_body,
            request=httpx.Request("POST", f"{client.base_url}/chat/completions"),
        )

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get, \
             patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_get.return_value = httpx.Response(
                status_code=200,
                json={"object": "list", "data": []},
                request=httpx.Request("GET", f"{client.base_url}/models"),
            )
            mock_post.side_effect = httpx.HTTPStatusError(
                message="Client error '404 Not Found'",
                request=mock_response.request,
                response=mock_response,
            )

            with self.assertRaises(MetaAIModelNotFoundError) as ctx:
                await client.chat("muse-spark-1.3", "system", "user")

            self.assertEqual(ctx.exception.status_code, 404)
            self.assertEqual(ctx.exception.error_code, "model_not_found")
            self.assertIn("muse-spark-1.3", ctx.exception.message)
            # Ensure no credentials leaked in error message
            self.assertNotIn(self.test_key, ctx.exception.message)

    async def test_authentication_failure_raises_structured_error(self):
        client = MetaAIClient()

        error_body = {
            "error": {
                "code": "invalid_api_key",
                "type": "authentication_error",
                "message": "Unauthorized",
            }
        }
        mock_response = httpx.Response(
            status_code=401,
            json=error_body,
            request=httpx.Request("POST", f"{client.base_url}/chat/completions"),
        )

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get, \
             patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_get.return_value = httpx.Response(
                status_code=401,
                json=error_body,
                request=httpx.Request("GET", f"{client.base_url}/models"),
            )
            mock_post.side_effect = httpx.HTTPStatusError(
                message="Client error '401 Unauthorized'",
                request=mock_response.request,
                response=mock_response,
            )

            with self.assertRaises(MetaAIAuthenticationError) as ctx:
                await client.chat("muse-spark-1.3", "system", "user")

            self.assertEqual(ctx.exception.status_code, 401)
            self.assertEqual(ctx.exception.error_code, "invalid_api_key")
            self.assertNotIn(self.test_key, ctx.exception.message)

    async def test_timeout_raises_meta_ai_timeout_error(self):
        client = MetaAIClient()

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get, \
             patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_get.side_effect = httpx.ReadTimeout("Read timed out")
            mock_post.side_effect = httpx.ReadTimeout("Read timed out")

            with self.assertRaises(MetaAITimeoutError) as ctx:
                await client.chat("muse-spark-1.3", "system", "user")

            self.assertEqual(ctx.exception.error_code, "timeout")
            self.assertNotIn(self.test_key, ctx.exception.message)

    async def test_concurrent_agent_calls_are_synchronized(self):
        client = MetaAIClient()
        get_calls = 0

        async def fake_get(*args, **kwargs):
            nonlocal get_calls
            get_calls += 1
            await asyncio.sleep(0.01)  # Simulate network latency
            return httpx.Response(
                status_code=200,
                json={"object": "list", "data": [{"id": "muse-spark-1.3", "object": "model"}]},
                request=httpx.Request("GET", f"{client.base_url}/models"),
            )

        async def fake_post(*args, **kwargs):
            await asyncio.sleep(0.01)
            return httpx.Response(
                status_code=200,
                json={
                    "id": "chatcmpl-concurrent",
                    "object": "chat.completion",
                    "model": "muse-spark-1.3",
                    "choices": [{"message": {"role": "assistant", "content": "OK"}}],
                },
                request=httpx.Request("POST", f"{client.base_url}/chat/completions"),
            )

        with patch("httpx.AsyncClient.get", side_effect=fake_get), \
             patch("httpx.AsyncClient.post", side_effect=fake_post):

            # Simulate market_intelligence and risk_manager running concurrently
            task1 = client.chat("muse-spark-1.3", "market prompt", "query 1")
            task2 = client.chat("muse-spark-1.3", "risk prompt", "query 2")

            results = await asyncio.gather(task1, task2)
            self.assertEqual(results, ["OK", "OK"])
            # Discovery should be executed only once due to asyncio.Lock and caching
            self.assertEqual(get_calls, 1)

    async def test_check_readiness_reporting(self):
        client = MetaAIClient()
        models_resp = httpx.Response(
            status_code=200,
            json={"object": "list", "data": [{"id": DEFAULT_META_MODEL, "object": "model"}]},
            request=httpx.Request("GET", f"{client.base_url}/models"),
        )
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = models_resp
            status = await client.check_readiness()
            self.assertEqual(status["status"], "ready")
            self.assertTrue(status["configured"])
            self.assertTrue(status["default_model_available"])
            self.assertEqual(status["model_count"], 1)
            # Ensure key itself is NOT in status dictionary
            self.assertNotIn(self.test_key, str(status))


if __name__ == "__main__":
    unittest.main()
