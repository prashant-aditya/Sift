"""Caching utilities (Redis + in-memory).

This package provides:
- `ResearchCache`: Redis-backed two-tier cache with stale-while-revalidate.
- `EmbeddingCache`: in-memory LRU cache for embeddings.
"""

from .embedding_cache import EmbeddingCache
from .redis_cache import CacheResult, ResearchCache

__all__ = ["CacheResult", "EmbeddingCache", "ResearchCache"]
