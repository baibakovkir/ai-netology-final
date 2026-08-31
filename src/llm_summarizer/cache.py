import asyncio
import hashlib
import json
import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class CacheEntry:
    value: str
    expires_at: float


class TTLCache:
    def __init__(
        self,
        ttl_seconds: int,
        max_entries: int,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._ttl_seconds = ttl_seconds
        self._max_entries = max_entries
        self._clock = clock
        self._entries: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> str | None:
        async with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            if entry.expires_at <= self._clock():
                del self._entries[key]
                return None
            self._entries.move_to_end(key)
            return entry.value

    async def set(self, key: str, value: str) -> None:
        async with self._lock:
            self._entries[key] = CacheEntry(value, self._clock() + self._ttl_seconds)
            self._entries.move_to_end(key)
            while len(self._entries) > self._max_entries:
                self._entries.popitem(last=False)


def make_cache_key(
    *, text: str, language: str, max_sentences: int, model: str, prompt_version: str
) -> str:
    normalized = " ".join(text.split())
    data = {
        "language": language,
        "max_sentences": max_sentences,
        "model": model,
        "prompt_version": prompt_version,
        "text": normalized,
    }
    encoded = json.dumps(data, ensure_ascii=False, sort_keys=True).encode()
    return hashlib.sha256(encoded).hexdigest()
