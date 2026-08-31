from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="APP_", extra="ignore", case_sensitive=False
    )

    environment: Literal["dev", "prod"] = "dev"
    log_level: str = "INFO"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: SecretStr = SecretStr("")
    llm_model: str = "gpt-4o-mini"
    llm_connect_timeout_seconds: float = Field(default=5.0, gt=0)
    llm_read_timeout_seconds: float = Field(default=30.0, gt=0)
    llm_retries: int = Field(default=2, ge=0, le=5)
    llm_retry_backoff_seconds: float = Field(default=0.25, ge=0, le=10)
    cache_ttl_seconds: int = Field(default=300, ge=1)
    cache_max_entries: int = Field(default=1024, ge=1)
    prompt_version: str = "v1"


@lru_cache
def get_settings() -> Settings:
    return Settings()
