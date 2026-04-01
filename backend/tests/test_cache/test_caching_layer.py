from __future__ import annotations

import json
from typing import Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.cache.embedding_cache import EmbeddingCache
from app.cache.redis_cache import CacheResult, ResearchCache
from app.core.orchestrator import ResearchOrchestrator
from app.ingestion.embedder import EmbeddingGenerator
from app.sources.registry import SourceRegistry


class _FakeAsyncRedis:
    def __init__(self) -> None:
        self._values: dict[str, str] = {}
        self._ttl: dict[str, int] = {}

    async def get(self, key: str) -> Optional[str]:
        return self._values.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        self._values[key] = value
        if ex is not None:
            self._ttl[key] = int(ex)

    async def ttl(self, key: str) -> int:
        return self._ttl.get(key, -2)


@pytest.mark.asyncio
async def test_hash_query_normalizes_casing_whitespace_and_punctuation():
    q1 = "  What is Redis?  "
    q2 = "what is redis"
    q3 = "WHAT IS REDIS!!!"
    assert ResearchCache.hash_query(q1) == ResearchCache.hash_query(q2) == ResearchCache.hash_query(q3)


@pytest.mark.asyncio
async def test_research_cache_fresh_vs_stale_detection():
    redis = _FakeAsyncRedis()
    cache = ResearchCache(redis, stale_threshold_seconds=3600 * 20, fresh_ttl_seconds=3600 * 24)
    qh = ResearchCache.hash_query("hello")

    await cache.set_research(qh, {"answer": "hi"})
    # Simulate "fresh" remaining TTL (> 20h)
    redis._ttl[f"sift:research:{qh}"] = 3600 * 21
    fresh = await cache.get_research(qh)
    assert fresh is not None and fresh.is_fresh

    # Simulate "stale" remaining TTL (<= 20h)
    redis._ttl[f"sift:research:{qh}"] = 3600 * 20
    stale = await cache.get_research(qh)
    assert stale is not None and not stale.is_fresh


@pytest.mark.asyncio
async def test_orchestrator_fresh_cache_hit_returns_without_running_pipeline():
    # Minimal orchestrator with mocks; cache hit should short-circuit before analyzer.decompose.
    mock_query_analyzer = MagicMock()
    mock_query_analyzer.decompose = pytest.fail  # type: ignore[assignment]

    orch = ResearchOrchestrator(
        query_analyzer=mock_query_analyzer,
        source_registry=SourceRegistry(),
        ingestion_pipeline=MagicMock(),
        vector_store=MagicMock(),
        embedder=MagicMock(),
        synthesizer=MagicMock(),
        cache=MagicMock(),
        celery_app=None,
    )

    orch._cache.get_research = AsyncMock(return_value=CacheResult(  # type: ignore[attr-defined]
        data={"answer": "cached", "citations": [], "sources_used": 1},
        ttl_seconds=3600 * 23,
        is_fresh=True,
    ))

    events = []
    async for ev in orch.research("Any query"):
        events.append({"event": ev["event"], "data": json.loads(ev["data"])})

    assert events[0]["event"] == "status"
    assert events[0]["data"]["phase"] == "cached"
    assert events[-1]["event"] == "complete"


@pytest.mark.asyncio
async def test_orchestrator_stale_cache_hit_triggers_refresh_when_celery_available():
    mock_query_analyzer = MagicMock()
    mock_query_analyzer.decompose = pytest.fail  # type: ignore[assignment]

    celery_app = MagicMock()
    sig = MagicMock()
    celery_app.signature.return_value = sig

    orch = ResearchOrchestrator(
        query_analyzer=mock_query_analyzer,
        source_registry=SourceRegistry(),
        ingestion_pipeline=MagicMock(),
        vector_store=MagicMock(),
        embedder=MagicMock(),
        synthesizer=MagicMock(),
        cache=MagicMock(),
        celery_app=celery_app,
    )

    orch._cache.get_research = AsyncMock(return_value=CacheResult(  # type: ignore[attr-defined]
        data={"answer": "stale", "citations": [], "sources_used": 1},
        ttl_seconds=3600 * 2,
        is_fresh=False,
    ))

    async for _ in orch.research("Any query", depth="standard"):
        pass

    assert celery_app.signature.called
    assert sig.apply_async.called


@pytest.mark.asyncio
async def test_embedding_cache_avoids_reembedding_identical_texts():
    cache = EmbeddingCache(max_entries=10_000)
    gen = EmbeddingGenerator(hf_api_token="", model_name="x", embedding_cache=cache)

    calls: list[list[str]] = []

    async def fake_embed_batch(texts: list[str]) -> list[list[float]]:
        calls.append(texts)
        return [[0.1] * 384 for _ in texts]

    gen._embed_batch = fake_embed_batch  # type: ignore[method-assign]

    texts = ["same text", "same text", "other"]
    emb1 = await gen.embed(texts)
    emb2 = await gen.embed(texts)

    assert len(emb1) == 3 and len(emb2) == 3
    # First call embeds unique missing texts; second call should embed nothing.
    assert len(calls) == 1
    stats = cache.stats()
    assert stats.hits > 0

