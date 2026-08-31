from typing import Literal

from pydantic import BaseModel, Field, field_validator


class SummaryRequest(BaseModel):
    text: str = Field(min_length=50, max_length=20_000)
    language: Literal["auto", "ru", "en"] = "auto"
    max_sentences: int = Field(default=5, ge=1, le=10)

    @field_validator("text")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if len(normalized) < 50:
            raise ValueError("text must contain at least 50 non-whitespace characters")
        return normalized


class SummaryResponse(BaseModel):
    summary: str
    source: Literal["llm", "fallback"]
    cached: bool
    request_id: str


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
