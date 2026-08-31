import logging
import time
from dataclasses import dataclass

from llm_summarizer.cache import TTLCache, make_cache_key
from llm_summarizer.config import Settings
from llm_summarizer.fallback import extractive_summary
from llm_summarizer.llm import LLMError, OpenAICompatibleClient
from llm_summarizer.postprocessing import EmptyModelResponseError, clean_summary
from llm_summarizer.prompt import build_prompt
from llm_summarizer.schemas import SummaryRequest

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SummaryResult:
    summary: str
    source: str
    cached: bool
    degraded: bool = False


class SummarizationService:
    def __init__(
        self, settings: Settings, llm_client: OpenAICompatibleClient, cache: TTLCache
    ) -> None:
        self._settings = settings
        self._llm_client = llm_client
        self._cache = cache

    async def summarize(self, request: SummaryRequest, request_id: str) -> SummaryResult:
        started = time.monotonic()
        key = make_cache_key(
            text=request.text,
            language=request.language,
            max_sentences=request.max_sentences,
            model=self._settings.llm_model,
            prompt_version=self._settings.prompt_version,
        )
        cached = await self._cache.get(key)
        if cached is not None:
            logger.info("cache_hit", extra={"request_id": request_id, "cache_key": key[:12]})
            return SummaryResult(summary=cached, source="llm", cached=True)

        logger.info("cache_miss", extra={"request_id": request_id, "cache_key": key[:12]})
        prompt = build_prompt(request.text, request.language, request.max_sentences)
        logger.info(
            "prompt_created",
            extra={
                "request_id": request_id,
                "prompt_version": self._settings.prompt_version,
                "text_length": len(request.text),
                "language": request.language,
            },
        )
        try:
            raw_summary = await self._llm_client.summarize(prompt, request_id)
            summary = clean_summary(raw_summary)
        except (LLMError, EmptyModelResponseError) as error:
            fallback = extractive_summary(request.text, request.max_sentences)
            logger.error(
                "summary_degraded",
                extra={"request_id": request_id, "error_type": type(error).__name__},
            )
            return SummaryResult(summary=fallback, source="fallback", cached=False, degraded=True)

        await self._cache.set(key, summary)
        logger.info(
            "summary_completed",
            extra={
                "request_id": request_id,
                "source": "llm",
                "latency_ms": round((time.monotonic() - started) * 1000, 2),
                "summary_length": len(summary),
            },
        )
        return SummaryResult(summary=summary, source="llm", cached=False)
