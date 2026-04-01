"""Research pipeline orchestration engine.

Coordinates query decomposition, multi-source search, ingestion, vector storage,
retrieval, and LLM synthesis into a single streaming SSE pipeline.  Each stage
yields structured SSE-compatible dicts consumed by ``EventSourceResponse``.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from collections.abc import AsyncGenerator
from typing import Any, Optional
from uuid import UUID

from app.cache.redis_cache import ResearchCache
from app.core.query_analyzer import QueryAnalyzer
from app.core.synthesizer import Synthesizer
from app.db.vector_store import VectorStore
from app.db.vector_store import RetrievedChunk
from app.ingestion.chunker import Chunk
from app.ingestion.embedder import EmbeddingGenerator
from app.ingestion.pipeline import IngestionPipeline
from app.retrieval.dense import DenseRetriever
from app.retrieval.hybrid_retriever import HybridRetriever
from app.sources.base import SourceAdapter, SourceResult
from app.sources.registry import SourceRegistry

logger = logging.getLogger(__name__)

DEPTH_CONFIG: dict[str, dict[str, int]] = {
    "quick": {"max_results_per_source": 3, "retrieval_top_k": 10},
    "standard": {"max_results_per_source": 5, "retrieval_top_k": 15},
    "deep": {"max_results_per_source": 10, "retrieval_top_k": 20},
}


def _sse_event(event: str, data: dict[str, Any]) -> dict[str, str]:
    """Build an SSE-compatible dict for sse-starlette's ``EventSourceResponse``."""
    return {"event": event, "data": json.dumps(data)}


def _build_frontend_citations(relevant: list[RetrievedChunk]) -> list[dict[str, Any]]:
    """Normalize retrieved chunks into the citation shape expected by the frontend.

    Frontend `Citation` shape (matches mock data):
      - id: number
      - title: string
      - url: string
      - source_name: string
      - relevance_score: number

    We intentionally emit `url` (not `source_url`) to prevent client-side
    `undefined.slice(...)` crashes.
    """
    citations: list[dict[str, Any]] = []
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
    return citations


class ResearchOrchestrator:
    """Orchestrates the full 7-step research pipeline, yielding SSE events.

    Parameters
    ----------
    query_analyzer:
        Decomposes user queries into focused sub-queries.
    source_registry:
        Provides access to registered source adapters.
    ingestion_pipeline:
        Extracts, chunks, and embeds source content.
    vector_store:
        Stores and retrieves chunks via cosine similarity.
    embedder:
        Generates query embeddings for retrieval.
    synthesizer:
        Streams cited answers from retrieved chunks via LLM.
    """

    def __init__(
        self,
        query_analyzer: QueryAnalyzer,
        source_registry: SourceRegistry,
        ingestion_pipeline: IngestionPipeline,
        vector_store: VectorStore,
        embedder: EmbeddingGenerator,
        synthesizer: Synthesizer,
        retriever: HybridRetriever | None = None,
        celery_app: Any | None = None,
        cache: ResearchCache | None = None,
        db_sessionmaker: Any | None = None,
    ) -> None:
        self._query_analyzer = query_analyzer
        self._source_registry = source_registry
        self._ingestion_pipeline = ingestion_pipeline
        self._vector_store = vector_store
        self._embedder = embedder
        self._synthesizer = synthesizer
        self._celery_app = celery_app
        self._cache = cache
        self._db_sessionmaker = db_sessionmaker
        self._retriever = retriever or HybridRetriever(
            dense=DenseRetriever(vector_store=vector_store, embedder=embedder)
        )

    async def _persist_session(
        self, session_id: str, *, user_id: UUID | None = None
    ) -> None:
        if self._db_sessionmaker is None:
            return
        try:
            from sqlalchemy import select

            from app.db.models import ResearchSession

            sid = UUID(session_id)
            async with self._db_sessionmaker() as db:
                existing = (
                    await db.execute(
                        select(ResearchSession).where(ResearchSession.id == sid)
                    )
                ).scalar_one_or_none()
                if existing is None:
                    db.add(ResearchSession(id=sid, user_id=user_id))
                    await db.commit()
                elif user_id is not None and existing.user_id is None:
                    existing.user_id = user_id
                    await db.commit()
        except Exception:
            logger.exception("Failed to persist research session")

    async def _persist_turn(
        self,
        *,
        session_id: str,
        user_id: UUID | None = None,
        query: str,
        answer: str,
        citations: list[dict[str, Any]],
        metrics: dict[str, Any],
    ) -> None:
        if self._db_sessionmaker is None:
            return
        try:
            from app.db.models import ResearchTurn

            sid = UUID(session_id)
            async with self._db_sessionmaker() as db:
                if user_id is not None:
                    # Best-effort ownership attachment. If the session row does not
                    # exist yet, it will be created by _persist_session().
                    try:
                        from app.db.models import ResearchSession

                        session = await db.get(ResearchSession, sid)
                        if session is not None and session.user_id is None:
                            session.user_id = user_id
                    except Exception:
                        # Never block the request on a failed ownership update.
                        pass

                db.add(
                    ResearchTurn(
                        id=uuid.uuid4(),
                        session_id=sid,
                        query=query,
                        answer=answer,
                        citations=citations,
                        metrics=metrics,
                    )
                )
                await db.commit()
        except Exception:
            logger.exception("Failed to persist research turn")

    async def followup(
        self,
        *,
        session_id: str,
        query: str,
        augmented_query: str,
        user_id: UUID | None = None,
        sources: Optional[list[str]] = None,
        depth: str = "standard",
    ) -> AsyncGenerator[dict[str, str], None]:
        """Run the research pipeline for an existing session (follow-up).

        Differences vs ``research``:
        - Uses the existing *session_id* (reuses the session-scoped Chroma collection)
        - Skips Tier-1 cache (the augmented query is inherently session-specific)
        - Persists the turn with the *original* query, while using *augmented_query*
          for retrieval/synthesis.
        """
        await self._persist_session(session_id, user_id=user_id)
        async for ev in self._run_pipeline(
            session_id=session_id,
            query=query,
            pipeline_query=augmented_query,
            sources=sources,
            depth=depth,
            enable_cache=False,
            user_id=user_id,
        ):
            yield ev

    async def _stream_cached_result(
        self, *, session_id: str, cached: dict[str, Any]
    ) -> AsyncGenerator[dict[str, str], None]:
        yield _sse_event("status", {"phase": "cached", "session_id": session_id})
        answer = str(cached.get("answer") or "")
        if answer:
            yield _sse_event("token", {"content": answer})

        complete_data: dict[str, Any] = {
            "session_id": session_id,
            "sources_used": int(cached.get("sources_used") or 0),
            "citations": cached.get("citations") or [],
        }
        if cached.get("errors"):
            complete_data["errors"] = cached["errors"]
        yield _sse_event("complete", complete_data)

    async def research(
        self,
        query: str,
        sources: Optional[list[str]] = None,
        depth: str = "standard",
        *,
        user_id: UUID | None = None,
    ) -> AsyncGenerator[dict[str, str], None]:
        """Execute the 7-step research pipeline as an SSE event stream.

        Yields dicts with ``event`` and ``data`` keys suitable for
        ``sse_starlette.EventSourceResponse``.

        Steps
        -----
        1. Decompose query into focused sub-queries
        2. Fan-out searches across sources via ``asyncio.gather``
        3. Ingest and embed source results
        4. Store embedded chunks in ChromaDB
        5. Retrieve top-K chunks via vector similarity
        6. Stream synthesis via LLM
        7. Yield completion event with ``session_id`` and citations
        """
        session_id = str(uuid.uuid4())
        await self._persist_session(session_id, user_id=user_id)
        async for ev in self._run_pipeline(
            session_id=session_id,
            query=query,
            pipeline_query=query,
            sources=sources,
            depth=depth,
            enable_cache=True,
            user_id=user_id,
        ):
            yield ev

    async def _run_pipeline(
        self,
        *,
        session_id: str,
        query: str,
        pipeline_query: str,
        sources: Optional[list[str]],
        depth: str,
        enable_cache: bool,
        user_id: UUID | None,
    ) -> AsyncGenerator[dict[str, str], None]:
        config = DEPTH_CONFIG.get(depth, DEPTH_CONFIG["standard"])
        query_hash = ResearchCache.hash_query(pipeline_query)
        start = time.perf_counter()

        # --- Cache check (Tier 1) ---
        if enable_cache and self._cache is not None:
            try:
                cache_result = await self._cache.get_research(query_hash)
            except Exception:
                cache_result = None

            if cache_result is not None and cache_result.is_fresh:
                cached_citations = cache_result.data.get("citations") or []
                cached_answer = str(cache_result.data.get("answer") or "")
                cached_sources_used = int(cache_result.data.get("sources_used") or 0)
                await self._persist_turn(
                    session_id=session_id,
                    user_id=user_id,
                    query=query,
                    answer=cached_answer,
                    citations=cached_citations,
                    metrics={
                        "depth": depth,
                        "cached": True,
                        "sources_used": cached_sources_used,
                        "duration_ms": int((time.perf_counter() - start) * 1000),
                    },
                )
                async for ev in self._stream_cached_result(
                    session_id=session_id, cached=cache_result.data
                ):
                    yield ev
                return

            if cache_result is not None and not cache_result.is_fresh:
                cached_citations = cache_result.data.get("citations") or []
                cached_answer = str(cache_result.data.get("answer") or "")
                cached_sources_used = int(cache_result.data.get("sources_used") or 0)
                await self._persist_turn(
                    session_id=session_id,
                    user_id=user_id,
                    query=query,
                    answer=cached_answer,
                    citations=cached_citations,
                    metrics={
                        "depth": depth,
                        "cached": True,
                        "stale": True,
                        "sources_used": cached_sources_used,
                        "duration_ms": int((time.perf_counter() - start) * 1000),
                    },
                )
                async for ev in self._stream_cached_result(
                    session_id=session_id, cached=cache_result.data
                ):
                    yield ev

                if self._celery_app is not None:
                    try:
                        self._celery_app.signature(
                            "workers.tasks.refresh_research",
                            kwargs={
                                "query_hash": query_hash,
                                "query": pipeline_query,
                                "sources": sources,
                                "depth": depth,
                            },
                            queue="ingestion",
                        ).apply_async()
                    except Exception:
                        logger.exception("Failed to enqueue cache refresh")
                return

        # --- Step 1: Analyze query → sub-queries ---
        yield _sse_event("status", {"phase": "decomposing", "session_id": session_id})
        sub_queries = await self._query_analyzer.decompose(pipeline_query)
        yield _sse_event(
            "status",
            {
                "phase": "decomposed",
                "sub_queries": sub_queries,
            },
        )

        # --- Step 2: Fan-out searches across sources ---
        adapters = self._resolve_adapters(sources)
        if not adapters:
            await self._persist_turn(
                session_id=session_id,
                user_id=user_id,
                query=query,
                answer="",
                citations=[],
                metrics={
                    "depth": depth,
                    "cached": False,
                    "sources_used": 0,
                    "errors": ["No available sources"],
                    "duration_ms": int((time.perf_counter() - start) * 1000),
                },
            )
            yield _sse_event(
                "complete",
                {
                    "session_id": session_id,
                    "sources_used": 0,
                    "citations": [],
                    "errors": ["No available sources"],
                },
            )
            return

        yield _sse_event(
            "status",
            {
                "phase": "searching",
                "sources_active": len(adapters),
                "sub_queries_count": len(sub_queries),
            },
        )

        (
            flat_results,
            source_errors,
            chunks,
            source_counts,
            sources_used,
        ) = await self._fan_out_searches(
            adapters,
            sub_queries,
            config["max_results_per_source"],
            session_id=session_id,
        )

        counts_iter = (
            source_counts or dict(_aggregate_source_counts(flat_results))
        ).items()
        for source_name, count in counts_iter:
            yield _sse_event(
                "source_complete",
                {
                    "source": source_name,
                    "results_count": count,
                },
            )

        if (sources_used or len(flat_results)) == 0:
            await self._persist_turn(
                session_id=session_id,
                user_id=user_id,
                query=query,
                answer="",
                citations=[],
                metrics={
                    "depth": depth,
                    "cached": False,
                    "sources_used": 0,
                    "errors": source_errors or None,
                    "duration_ms": int((time.perf_counter() - start) * 1000),
                },
            )
            yield _sse_event(
                "complete",
                {
                    "session_id": session_id,
                    "sources_used": 0,
                    "citations": [],
                    "errors": source_errors or None,
                },
            )
            return

        # --- Step 3-4: Ingest + store (done locally or via Celery chord callback) ---
        if chunks is None:
            yield _sse_event(
                "status",
                {
                    "phase": "processing",
                    "results_count": sources_used or len(flat_results),
                },
            )
            chunks = await self._ingestion_pipeline.process(flat_results)

            if not chunks:
                await self._persist_turn(
                    session_id=session_id,
                    user_id=user_id,
                    query=query,
                    answer="",
                    citations=[],
                    metrics={
                        "depth": depth,
                        "cached": False,
                        "sources_used": len(flat_results),
                        "chunks_count": 0,
                        "duration_ms": int((time.perf_counter() - start) * 1000),
                    },
                )
                yield _sse_event(
                    "complete",
                    {
                        "session_id": session_id,
                        "sources_used": len(flat_results),
                        "citations": [],
                    },
                )
                return

            yield _sse_event(
                "status", {"phase": "storing", "chunks_count": len(chunks)}
            )
            collection_name = VectorStore.collection_name_for_session(session_id)
            upserted = await asyncio.to_thread(
                self._vector_store.upsert_chunks,
                collection_name,
                chunks,
            )
            logger.info("Stored %d chunks for session %s", upserted, session_id)
        else:
            yield _sse_event(
                "status",
                {
                    "phase": "processing",
                    "results_count": sources_used or len(flat_results),
                },
            )
            yield _sse_event(
                "status", {"phase": "storing", "chunks_count": len(chunks)}
            )

        # --- Step 5: Retrieve top-K via hybrid retrieval (BM25 + dense) ---
        yield _sse_event("status", {"phase": "retrieving"})
        relevant = await self._retriever.retrieve(
            query=pipeline_query,
            session_id=session_id,
            chunks=chunks,
            top_k=config["retrieval_top_k"],
        )

        # --- Step 6: Stream synthesis via LLM ---
        yield _sse_event("status", {"phase": "synthesizing"})
        full_answer = ""
        async for token in self._synthesizer.synthesize(pipeline_query, relevant):
            full_answer += token
            yield _sse_event("token", {"content": token})

        # --- Step 7: Complete ---
        citations = _build_frontend_citations(relevant)
        complete_data: dict[str, Any] = {
            "session_id": session_id,
            "sources_used": sources_used or len(flat_results),
            "citations": citations,
        }
        if source_errors:
            complete_data["errors"] = source_errors
        yield _sse_event("complete", complete_data)
        await self._persist_turn(
            session_id=session_id,
            user_id=user_id,
            query=query,
            answer=full_answer,
            citations=citations,
            metrics={
                "depth": depth,
                "cached": False,
                "sources_used": sources_used or len(flat_results),
                "chunks_count": len(chunks),
                "errors": source_errors or None,
                "duration_ms": int((time.perf_counter() - start) * 1000),
                "pipeline_query_augmented": pipeline_query != query,
            },
        )

        # --- Cache store (Tier 1 + Tier 2) ---
        if enable_cache and self._cache is not None:
            try:
                await self._cache.set_research(
                    query_hash,
                    {
                        "answer": full_answer,
                        "citations": citations,
                        "sources_used": sources_used or len(flat_results),
                        "errors": source_errors or None,
                    },
                )

                by_source: dict[str, list[dict[str, Any]]] = {}
                for r in flat_results:
                    by_source.setdefault(r.source_name, []).append(r.model_dump())
                for src, data in by_source.items():
                    await self._cache.set_source_results(src, query_hash, data)
            except Exception:
                logger.exception("Failed to write research cache")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_adapters(self, sources: Optional[list[str]]) -> list[SourceAdapter]:
        """Map requested source names to available adapters.

        Falls back to all available adapters when *sources* is ``None`` or
        none of the requested names match a registered, available adapter.
        """
        if sources is None:
            return self._source_registry.get_available()

        adapters: list[SourceAdapter] = []
        for name in sources:
            adapter = self._source_registry.get(name)
            if adapter and adapter.is_available():
                adapters.append(adapter)
            else:
                logger.warning("Requested source '%s' not available; skipping", name)

        return adapters if adapters else self._source_registry.get_available()

    async def _fan_out_searches(
        self,
        adapters: list[SourceAdapter],
        sub_queries: list[str],
        max_results: int,
        *,
        session_id: str,
    ) -> tuple[
        list[SourceResult],
        list[str],
        list[Chunk] | None,
        dict[str, int] | None,
        int | None,
    ]:
        """Search all sources concurrently, optionally via Celery chord.

        Returns:
          - flat list of SourceResult
          - list of error strings
          - chunks (when Celery chord performs ingestion+upsert), else None
        """
        if self._celery_app is not None:
            return await self._fan_out_searches_celery(
                adapters=adapters,
                sub_queries=sub_queries,
                max_results=max_results,
                session_id=session_id,
            )

        tasks = [
            self._safe_search(adapter, sub_query, max_results)
            for adapter in adapters
            for sub_query in sub_queries
        ]
        search_outcomes = await asyncio.gather(*tasks)

        flat_results: list[SourceResult] = []
        errors: list[str] = []
        for outcome in search_outcomes:
            flat_results.extend(outcome["results"])
            if outcome["error"]:
                errors.append(f"{outcome['source']}: {outcome['error']}")

        source_counts = dict(_aggregate_source_counts(flat_results))
        return flat_results, errors, None, source_counts, len(flat_results)

    async def _fan_out_searches_celery(
        self,
        *,
        adapters: list[SourceAdapter],
        sub_queries: list[str],
        max_results: int,
        session_id: str,
    ) -> tuple[
        list[SourceResult],
        list[str],
        list[Chunk] | None,
        dict[str, int] | None,
        int | None,
    ]:
        """Dispatch source fan-out via Celery chord(group(...))(callback)."""
        from celery import chord

        # Use task names to avoid importing worker modules in the web process.
        header = [
            self._celery_app.signature(
                "workers.tasks.search_source",
                kwargs={
                    "source_name": a.name,
                    "sub_queries": sub_queries,
                    "max_results": max_results,
                },
                queue="search",
            )
            for a in adapters
        ]
        callback = self._celery_app.signature(
            "workers.callbacks.process_results",
            kwargs={"session_id": session_id},
            queue="ingestion",
        )

        async_result = chord(header)(callback)

        def _wait():
            # Worst-case includes header tasks + callback; keep a generous bound.
            return async_result.get(timeout=90)

        payload: dict[str, Any] = await asyncio.to_thread(_wait)

        errors: list[str] = payload.get("errors") or []
        source_counts = payload.get("source_counts") or {}
        sources_used = int(payload.get("sources_used") or 0)
        chunks_payload = payload.get("chunks") or []
        chunks: list[Chunk] = []
        for raw in chunks_payload:
            try:
                chunks.append(Chunk(**raw))
            except Exception as exc:
                errors.append(f"ingestion: invalid_chunk_payload ({exc})")

        return [], errors, chunks, source_counts, sources_used

    @staticmethod
    async def _safe_search(
        adapter: SourceAdapter,
        query: str,
        max_results: int,
    ) -> dict[str, Any]:
        """Execute a single adapter search, catching and logging any exception."""
        try:
            results = await adapter.search(query, max_results=max_results)
            return {"source": adapter.name, "results": results, "error": None}
        except Exception as exc:
            logger.error(
                "Source '%s' failed for query '%s': %s",
                adapter.name,
                query,
                exc,
            )
            return {"source": adapter.name, "results": [], "error": str(exc)}


def _aggregate_source_counts(results: list[SourceResult]) -> list[tuple[str, int]]:
    """Aggregate result counts by source name for ``source_complete`` events."""
    counts: dict[str, int] = {}
    for r in results:
        counts[r.source_name] = counts.get(r.source_name, 0) + 1
    return list(counts.items())
