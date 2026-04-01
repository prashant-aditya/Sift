from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Iterable, Optional

from cachetools import LRUCache


def _sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class EmbeddingCacheStats:
    hits: int
    misses: int


class EmbeddingCache:
    """In-memory LRU cache for embeddings.

    Key: sha256(text) -> Value: embedding vector (list[float])
    """

    def __init__(self, *, max_entries: int = 10_000) -> None:
        self._cache: LRUCache[str, list[float]] = LRUCache(maxsize=max_entries)
        self._hits = 0
        self._misses = 0

    @staticmethod
    def key_for_text(text: str) -> str:
        return _sha256_hex(text)

    def get(self, text: str) -> Optional[list[float]]:
        key = self.key_for_text(text)
        val = self._cache.get(key)
        if val is None:
            self._misses += 1
            return None
        self._hits += 1
        return val

    def set(self, text: str, embedding: list[float]) -> None:
        key = self.key_for_text(text)
        self._cache[key] = embedding

    def bulk_get(self, texts: Iterable[str]) -> dict[str, list[float]]:
        found: dict[str, list[float]] = {}
        for t in texts:
            emb = self.get(t)
            if emb is not None:
                found[t] = emb
        return found

    def stats(self) -> EmbeddingCacheStats:
        return EmbeddingCacheStats(hits=self._hits, misses=self._misses)
