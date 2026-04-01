"""Celery tasks for source search fan-out."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.cache.redis_cache import ResearchCache
from app.config import get_settings
from app.core.query_analyzer import QueryAnalyzer
from app.core.synthesizer import Synthesizer
from app.db.vector_store import VectorStore
from app.ingestion.embedder import EmbeddingGenerator
from app.ingestion.pipeline import IngestionPipeline
from app.resilience.circuit_breaker import CircuitBreaker, CircuitOpenError
from app.resilience.rate_limiter import TokenBucketRateLimiter
from app.resilience.retry import RetryError, with_retry
from app.retrieval.dense import DenseRetriever
from app.retrieval.hybrid_retriever import HybridRetriever
from app.sources.base import SourceResult
from app.sources.arxiv import ArxivAdapter
from app.sources.duckduckgo import DuckDuckGoAdapter
from app.sources.hackernews import HackerNewsAdapter
from app.sources.reddit import RedditAdapter
from app.sources.registry import SourceRegistry
from app.sources.wikipedia import WikipediaAdapter
from redis.asyncio import Redis
from workers.celery_app import celery_app
from celery.exceptions import Retry

logger = logging.getLogger(__name__)


def _build_source_registry() -> SourceRegistry:
    registry = SourceRegistry()
    registry.register(DuckDuckGoAdapter())
    registry.register(WikipediaAdapter())
    registry.register(HackerNewsAdapter())
    registry.register(ArxivAdapter())
    registry.register(RedditAdapter())
    return registry


def _run_async(coro):
    # Celery tasks run in a sync context; run async adapter code safely.
    return asyncio.run(coro)


@celery_app.task(
    name="workers.tasks.search_source",
    bind=True,
    max_retries=2,
    default_retry_delay=2,
)
def search_source(  # type: ignore[no-untyped-def]
    self,
    *,
    source_name: str,
    sub_queries: list[str],
    max_results: int,
) -> dict[str, Any]:
    """Search a single source adapter with all sub-queries.

    Returns a JSON-serializable dict:
      { "source": str, "results": list[dict], "error": str|None }
    """
    try:
        settings = get_settings()
        registry = _build_source_registry()
        adapter = registry.get(source_name)
        if adapter is None or not adapter.is_available():
            return {
                "source": source_name,
                "results": [],
                "error": "source_not_available",
            }

        async def _run() -> tuple[list[SourceResult], str | None]:
            redis = None
            circuit_breaker = None
            rate_limiter = None
            try:
                # Create inside the event loop to avoid "no current event loop" issues.
                redis = Redis.from_url(settings.redis_url, decode_responses=True)
                # If Redis isn't reachable (e.g., local unit tests), fail open.
                await redis.ping()
                circuit_breaker = CircuitBreaker(source_name, redis)
                rate_limiter = TokenBucketRateLimiter(redis)
            except Exception:
                if redis is not None:
                    try:
                        await redis.aclose()
                    except Exception:
                        pass
                redis = None

            @with_retry(max_retries=2, backoff_base=1.0)
            async def _search_once(q: str) -> list[SourceResult]:
                if circuit_breaker is None or rate_limiter is None:
                    return await adapter.search(q, max_results=max_results)

                async with circuit_breaker:
                    ok = await rate_limiter.acquire(source_name, timeout=10.0)
                    if not ok:
                        raise TimeoutError("rate_limiter_timeout")
                    return await adapter.search(q, max_results=max_results)

            flat: list[SourceResult] = []
            error: str | None = None
            for q in sub_queries:
                try:
                    flat.extend(await _search_once(q))
                except CircuitOpenError as exc:
                    logger.warning(
                        "circuit open source=%s retry_after=%ss",
                        source_name,
                        exc.retry_after_seconds,
                    )
                    error = "circuit_open"
                    break
                except RetryError as exc:
                    logger.warning(
                        "retries exhausted source=%s err=%s", source_name, str(exc)
                    )
                    raise
                except Exception:
                    logger.exception("search failed source=%s query=%s", source_name, q)
                    raise
            try:
                if redis is not None:
                    await redis.aclose()
            except Exception:
                pass
            return flat, error

        all_results, error = _run_async(_run())

        payload = [r.model_dump() for r in all_results]
        return {"source": source_name, "results": payload, "error": error}
    except Exception as exc:
        logger.exception("search_source failed source=%s", source_name)
        try:
            raise self.retry(exc=exc)
        except Retry:
            raise
        except Exception:
            # On final failure Celery raises; return a structured error for safety
            # (not typically reached when retries are exhausted).
            return {"source": source_name, "results": [], "error": str(exc)}


@celery_app.task(name="workers.tasks.refresh_research")
def refresh_research(  # type: ignore[no-untyped-def]
    *,
    query_hash: str,
    query: str,
    sources: list[str] | None = None,
    depth: str = "standard",
) -> dict[str, Any]:
    """Background refresh for stale-while-revalidate.

    Recomputes the research answer and updates Tier-1 cache.
    """
    settings = get_settings()
    cache = ResearchCache.from_url(settings.redis_url)

    registry = _build_source_registry()
    if sources:
        adapters = [
            a for a in (registry.get(s) for s in sources) if a and a.is_available()
        ]
    else:
        adapters = registry.get_available()

    analyzer = QueryAnalyzer()
    embedder = EmbeddingGenerator(
        hf_api_token=settings.hf_api_token,
        model_name=settings.embedding_model,
    )
    ingestion = IngestionPipeline(embedder=embedder)
    store = VectorStore()
    retriever = HybridRetriever(
        dense=DenseRetriever(vector_store=store, embedder=embedder)
    )
    synthesizer = Synthesizer()

    async def _run() -> dict[str, Any]:
        sub_queries = await analyzer.decompose(query)

        flat: list[SourceResult] = []
        for adapter in adapters:
            for sq in sub_queries:
                try:
                    results = await adapter.search(sq, max_results=5)
                    flat.extend(results)
                except Exception:
                    logger.exception(
                        "refresh_research search failed source=%s", adapter.name
                    )

        if not flat:
            await cache.set_research(
                query_hash, {"answer": "", "citations": [], "sources_used": 0}
            )
            return {"ok": True, "sources_used": 0}

        chunks = await ingestion.process(flat)
        if not chunks:
            await cache.set_research(
                query_hash, {"answer": "", "citations": [], "sources_used": len(flat)}
            )
            return {"ok": True, "sources_used": len(flat)}

        # Store to a deterministic session collection keyed by query_hash.
        session_id = f"cache_{query_hash[:12]}"
        collection_name = VectorStore.collection_name_for_session(session_id)
        store.upsert_chunks(collection_name, chunks)

        relevant = await retriever.retrieve(
            query=query, session_id=session_id, chunks=chunks, top_k=15
        )

        answer = ""
        async for tok in synthesizer.synthesize(query, relevant):
            answer += tok

        citations = []
        for idx, rc in enumerate(relevant, start=1):
            url = rc.chunk.source_url or ""
            title = rc.chunk.source_title or url or "Untitled source"
            source_name = rc.chunk.source_name or "unknown"
            citations.append(
                {
                    "id": idx,
                    "title": title,
                    "url": url,
                    "source_name": source_name,
                    "relevance_score": float(rc.score),
                }
            )

        await cache.set_research(
            query_hash,
            {
                "answer": answer,
                "citations": citations,
                "sources_used": len(flat),
                "errors": None,
            },
        )
        return {"ok": True, "sources_used": len(flat)}

    return _run_async(_run())
