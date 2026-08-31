import asyncio
import logging
from typing import Any

import httpx

from llm_summarizer.config import Settings
from llm_summarizer.prompt import Prompt

logger = logging.getLogger(__name__)


class LLMError(RuntimeError):
    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


class OpenAICompatibleClient:
    def __init__(self, settings: Settings, http_client: httpx.AsyncClient) -> None:
        self._settings = settings
        self._http_client = http_client

    async def summarize(self, prompt: Prompt, request_id: str) -> str:
        api_key = self._settings.llm_api_key.get_secret_value()
        if not api_key:
            raise LLMError("LLM API key is not configured")

        attempts = self._settings.llm_retries + 1
        last_error: LLMError | None = None
        for attempt in range(1, attempts + 1):
            try:
                return await self._request(prompt)
            except LLMError as error:
                last_error = error
                logger.error(
                    "llm_attempt_failed",
                    extra={
                        "request_id": request_id,
                        "attempt": attempt,
                        "attempts": attempts,
                        "retryable": error.retryable,
                        "error_type": type(error).__name__,
                    },
                )
                if not error.retryable or attempt == attempts:
                    raise
                await asyncio.sleep(self._settings.llm_retry_backoff_seconds * attempt)
        raise last_error or LLMError("LLM request failed")

    async def _request(self, prompt: Prompt) -> str:
        url = f"{self._settings.llm_base_url.rstrip('/')}/chat/completions"
        headers = {"Authorization": f"Bearer {self._settings.llm_api_key.get_secret_value()}"}
        payload = {
            "model": self._settings.llm_model,
            "messages": [
                {"role": "system", "content": prompt.system},
                {"role": "user", "content": prompt.user},
            ],
            "temperature": 0.2,
        }
        try:
            response = await self._http_client.post(url, headers=headers, json=payload)
        except httpx.TransportError as error:
            raise LLMError("LLM network request failed", retryable=True) from error

        if response.status_code >= 400:
            retryable = response.status_code == 429 or response.status_code >= 500
            raise LLMError(f"LLM returned HTTP {response.status_code}", retryable=retryable)
        try:
            body: dict[str, Any] = response.json()
            content = body["choices"][0]["message"]["content"]
            if not isinstance(content, str):
                raise TypeError("content is not a string")
            return content
        except (KeyError, IndexError, TypeError, ValueError) as error:
            raise LLMError("LLM returned an invalid response") from error
