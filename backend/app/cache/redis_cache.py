from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Optional

from redis.asyncio import Redis

_PUNCT_RE = re.compile(r"[^\w\s]", flags=re.UNICODE)


@dataclass(frozen=True)
class CacheResult:
    data: dict[str, Any]
    ttl_seconds: int
    is_fresh: bool


class ResearchCache:
    """Redis-backed two-tier cache with stale-while-revalidate semantics.

    Tier 1: query hash -> full synthesized result (TTL: 24 hours)
    Tier 2: source + query hash -> raw source results (TTL: 6 hours)
    """

    def __init__(
        self,
        redis: Redis,
        *,
        fresh_ttl_seconds: int = 3600 * 24,
        stale_threshold_seconds: int = 3600 * 20,
        source_ttl_seconds: int = 3600 * 6,
        key_prefix: str = "sift",
    ) -> None:
        self.redis = redis
        self.fresh_ttl = int(fresh_ttl_seconds)
        self.stale_threshold = int(stale_threshold_seconds)
        self.source_ttl = int(source_ttl_seconds)
        self._prefix = key_prefix.strip(":")

    @classmethod
    def from_url(cls, redis_url: str, **kwargs: Any) -> "ResearchCache":
        redis = Redis.from_url(redis_url, decode_responses=True)
        return cls(redis, **kwargs)

    def _key_research(self, query_hash: str) -> str:
        return f"{self._prefix}:research:{query_hash}"

    def _key_source(self, source: str, query_hash: str) -> str:
        safe_source = source.strip().lower()
        return f"{self._prefix}:source:{safe_source}:{query_hash}"

    async def get_research(self, query_hash: str) -> Optional[CacheResult]:
        key = self._key_research(query_hash)
        raw, ttl = await self.redis.get(key), await self.redis.ttl(key)
        if raw is None:
            return None
        if ttl is None or ttl < 0:
            # Treat missing/unknown TTL as stale to be safe.
            ttl_seconds = 0
        else:
            ttl_seconds = int(ttl)

        try:
            data = json.loads(raw)
            if not isinstance(data, dict):
                return None
        except Exception:
            return None

        is_fresh = ttl_seconds > self.stale_threshold
        return CacheResult(data=data, ttl_seconds=ttl_seconds, is_fresh=is_fresh)

    async def set_research(self, query_hash: str, data: dict[str, Any]) -> None:
        key = self._key_research(query_hash)
        payload = json.dumps(data, ensure_ascii=False)
        await self.redis.set(key, payload, ex=self.fresh_ttl)

    async def get_source_results(
        self, source: str, query_hash: str
    ) -> Optional[list[dict[str, Any]]]:
        key = self._key_source(source, query_hash)
        raw = await self.redis.get(key)
        if raw is None:
            return None
        try:
            data = json.loads(raw)
            if not isinstance(data, list):
                return None
            out: list[dict[str, Any]] = []
            for item in data:
                if isinstance(item, dict):
                    out.append(item)
            return out
        except Exception:
            return None

    async def set_source_results(
        self, source: str, query_hash: str, data: list[dict[str, Any]]
    ) -> None:
        key = self._key_source(source, query_hash)
        payload = json.dumps(data, ensure_ascii=False)
        await self.redis.set(key, payload, ex=self.source_ttl)

    @staticmethod
    def hash_query(query: str) -> str:
        normalized = query.strip().lower()
        normalized = _PUNCT_RE.sub("", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
