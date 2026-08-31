import pytest

from llm_summarizer.cache import TTLCache, make_cache_key


@pytest.mark.asyncio
async def test_cache_hit_and_expiry() -> None:
    now = 10.0
    cache = TTLCache(ttl_seconds=5, max_entries=2, clock=lambda: now)
    await cache.set("key", "value")
    assert await cache.get("key") == "value"

    now = 16.0
    assert await cache.get("key") is None


@pytest.mark.asyncio
async def test_cache_evicts_oldest_entry() -> None:
    cache = TTLCache(ttl_seconds=10, max_entries=2)
    await cache.set("one", "1")
    await cache.set("two", "2")
    await cache.set("three", "3")
    assert await cache.get("one") is None
    assert await cache.get("two") == "2"


def test_cache_key_uses_all_request_parameters() -> None:
    base = make_cache_key(
        text="Some   sufficiently long source text.",
        language="auto",
        max_sentences=5,
        model="model-a",
        prompt_version="v1",
    )
    whitespace_equivalent = make_cache_key(
        text="Some sufficiently long source text.",
        language="auto",
        max_sentences=5,
        model="model-a",
        prompt_version="v1",
    )
    changed_language = make_cache_key(
        text="Some sufficiently long source text.",
        language="ru",
        max_sentences=5,
        model="model-a",
        prompt_version="v1",
    )
    assert base == whitespace_equivalent
    assert base != changed_language
