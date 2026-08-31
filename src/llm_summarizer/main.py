import logging
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request, Response, status

from llm_summarizer.cache import TTLCache
from llm_summarizer.config import Settings, get_settings
from llm_summarizer.llm import OpenAICompatibleClient
from llm_summarizer.logging import configure_logging
from llm_summarizer.schemas import HealthResponse, SummaryRequest, SummaryResponse
from llm_summarizer.service import SummarizationService

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        configure_logging(app_settings.log_level)
        timeout = httpx.Timeout(
            connect=app_settings.llm_connect_timeout_seconds,
            read=app_settings.llm_read_timeout_seconds,
            write=app_settings.llm_read_timeout_seconds,
            pool=app_settings.llm_connect_timeout_seconds,
        )
        async with httpx.AsyncClient(timeout=timeout) as http_client:
            app.state.summary_service = SummarizationService(
                settings=app_settings,
                llm_client=OpenAICompatibleClient(app_settings, http_client),
                cache=TTLCache(
                    ttl_seconds=app_settings.cache_ttl_seconds,
                    max_entries=app_settings.cache_max_entries,
                ),
            )
            yield

    app = FastAPI(
        title="LLM Summarizer",
        version="0.1.0",
        description="Summarize text with an OpenAI-compatible LLM and a local fallback.",
        lifespan=lifespan,
    )

    @app.get("/health", response_model=HealthResponse, tags=["operations"])
    async def health() -> HealthResponse:
        return HealthResponse()

    @app.post(
        "/v1/summaries",
        response_model=SummaryResponse,
        responses={
            503: {"model": SummaryResponse, "description": "LLM unavailable; fallback used"}
        },
        tags=["summaries"],
    )
    async def summarize(
        payload: SummaryRequest, request: Request, response: Response
    ) -> SummaryResponse:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        logger.info(
            "request_received",
            extra={"request_id": request_id, "path": str(request.url.path)},
        )
        service: SummarizationService = request.app.state.summary_service
        result = await service.summarize(payload, request_id)
        if result.degraded:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        response.headers["X-Request-ID"] = request_id
        return SummaryResponse(
            summary=result.summary,
            source=result.source,
            cached=result.cached,
            request_id=request_id,
        )

    return app


app = create_app()
