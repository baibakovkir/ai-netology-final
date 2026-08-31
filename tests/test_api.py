from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
import pytest

from llm_summarizer.config import Settings
from llm_summarizer.main import create_app
from llm_summarizer.service import SummaryResult

TEXT = (
    "Это достаточно длинный исходный текст для проверки HTTP API сервиса. "
    "Он состоит из нескольких предложений и корректно проходит валидацию."
)


class StubService:
    def __init__(self, result: SummaryResult) -> None:
        self.result = result

    async def summarize(self, payload: object, request_id: str) -> SummaryResult:
        return self.result


@asynccontextmanager
async def api_client(result: SummaryResult) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app(Settings(_env_file=None))
    async with app.router.lifespan_context(app):
        app.state.summary_service = StubService(result)
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


@pytest.mark.asyncio
async def test_success_response_and_request_id() -> None:
    async with api_client(SummaryResult("Результат.", "llm", False)) as client:
        response = await client.post(
            "/v1/summaries", json={"text": TEXT}, headers={"X-Request-ID": "known-id"}
        )
    assert response.status_code == 200
    assert response.json() == {
        "summary": "Результат.",
        "source": "llm",
        "cached": False,
        "request_id": "known-id",
    }
    assert response.headers["X-Request-ID"] == "known-id"


@pytest.mark.asyncio
async def test_degraded_response_has_503_and_fallback_body() -> None:
    result = SummaryResult("Запасное резюме.", "fallback", False, degraded=True)
    async with api_client(result) as client:
        response = await client.post("/v1/summaries", json={"text": TEXT})
    assert response.status_code == 503
    assert response.json()["source"] == "fallback"
    assert response.json()["summary"] == "Запасное резюме."


@pytest.mark.asyncio
async def test_validation_error() -> None:
    async with api_client(SummaryResult("unused", "llm", False)) as client:
        response = await client.post("/v1/summaries", json={"text": "too short"})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_health() -> None:
    async with api_client(SummaryResult("unused", "llm", False)) as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
