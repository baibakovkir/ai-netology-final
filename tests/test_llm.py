import httpx
import pytest
from pydantic import SecretStr

from llm_summarizer.config import Settings
from llm_summarizer.llm import LLMError, OpenAICompatibleClient
from llm_summarizer.prompt import Prompt


def settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "llm_api_key": SecretStr("test-key"),
        "llm_retries": 2,
        "llm_retry_backoff_seconds": 0,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


@pytest.mark.asyncio
async def test_client_retries_retryable_status() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls < 3:
            return httpx.Response(500, json={"error": "temporary"})
        return httpx.Response(200, json={"choices": [{"message": {"content": "Summary"}}]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = OpenAICompatibleClient(settings(), http_client)
        result = await client.summarize(Prompt("system", "user"), "request-1")
    assert result == "Summary"
    assert calls == 3


@pytest.mark.asyncio
async def test_client_does_not_retry_authentication_error() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(401, json={"error": "unauthorized"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = OpenAICompatibleClient(settings(), http_client)
        with pytest.raises(LLMError, match="401"):
            await client.summarize(Prompt("system", "user"), "request-1")
    assert calls == 1


@pytest.mark.asyncio
async def test_client_rejects_missing_key_without_network_call() -> None:
    async with httpx.AsyncClient() as http_client:
        client = OpenAICompatibleClient(settings(llm_api_key=SecretStr("")), http_client)
        with pytest.raises(LLMError, match="not configured"):
            await client.summarize(Prompt("system", "user"), "request-1")


@pytest.mark.asyncio
async def test_client_rejects_invalid_response_shape() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": None}}]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = OpenAICompatibleClient(settings(), http_client)
        with pytest.raises(LLMError, match="invalid response"):
            await client.summarize(Prompt("system", "user"), "request-1")
