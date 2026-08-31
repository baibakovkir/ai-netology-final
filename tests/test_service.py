import pytest
from pydantic import SecretStr

from llm_summarizer.cache import TTLCache
from llm_summarizer.config import Settings
from llm_summarizer.llm import LLMError
from llm_summarizer.schemas import SummaryRequest
from llm_summarizer.service import SummarizationService

TEXT = (
    "Это достаточно длинное первое предложение для проверки сервиса. "
    "Второе предложение содержит дополнительные сведения. Третье завершает текст."
)


class FakeLLM:
    def __init__(self, response: str = "Краткий ответ.", error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.calls = 0

    async def summarize(self, prompt: object, request_id: str) -> str:
        self.calls += 1
        if self.error:
            raise self.error
        return self.response


def make_service(llm: FakeLLM) -> SummarizationService:
    config = Settings(_env_file=None, llm_api_key=SecretStr("test"))
    return SummarizationService(config, llm, TTLCache(ttl_seconds=60, max_entries=10))  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_success_is_cached() -> None:
    llm = FakeLLM()
    service = make_service(llm)
    request = SummaryRequest(text=TEXT)
    first = await service.summarize(request, "one")
    second = await service.summarize(request, "two")
    assert first.source == "llm" and first.cached is False
    assert second.source == "llm" and second.cached is True
    assert llm.calls == 1


@pytest.mark.asyncio
async def test_failure_returns_uncached_fallback() -> None:
    llm = FakeLLM(error=LLMError("offline", retryable=True))
    service = make_service(llm)
    request = SummaryRequest(text=TEXT, max_sentences=1)
    first = await service.summarize(request, "one")
    second = await service.summarize(request, "two")
    assert first.source == "fallback" and first.degraded
    assert first.summary == "Это достаточно длинное первое предложение для проверки сервиса."
    assert second.cached is False
    assert llm.calls == 2


@pytest.mark.asyncio
async def test_empty_model_response_uses_fallback() -> None:
    result = await make_service(FakeLLM(response="   ")).summarize(SummaryRequest(text=TEXT), "one")
    assert result.source == "fallback"
    assert result.degraded
