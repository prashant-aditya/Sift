"""Research pipeline orchestration engine.

Coordinates query decomposition, multi-source search, ingestion, vector storage,
retrieval, and LLM synthesis into a single streaming SSE pipeline.  Each stage
yields structured SSE-compatible dicts consumed by ``EventSourceResponse``.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections.abc import AsyncGenerator
from typing import Any, Optional

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
    ) -> None:
        self._query_analyzer = query_analyzer
        self._source_registry = source_registry
        self._ingestion_pipeline = ingestion_pipeline
        self._vector_store = vector_store
        self._embedder = embedder
        self._synthesizer = synthesizer
        self._celery_app = celery_app
        self._retriever = retriever or HybridRetriever(
            dense=DenseRetriever(vector_store=vector_store, embedder=embedder)
        )

    async def research(
        self,
        query: str,
        sources: Optional[list[str]] = None,
        depth: str = "standard",
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
        config = DEPTH_CONFIG.get(depth, DEPTH_CONFIG["standard"])
        session_id = f"session_{uuid.uuid4().hex[:12]}"

        # --- Step 1: Analyze query → sub-queries ---
        yield _sse_event("status", {"phase": "decomposing", "session_id": session_id})
        sub_queries = await self._query_analyzer.decompose(query)
        yield _sse_event("status", {
            "phase": "decomposed",
            "sub_queries": sub_queries,
        })

        # --- Step 2: Fan-out searches across sources ---
        adapters = self._resolve_adapters(sources)
        if not adapters:
            yield _sse_event("complete", {
                "session_id": session_id,
                "sources_used": 0,
                "citations": [],
                "errors": ["No available sources"],
            })
            return

        yield _sse_event("status", {
            "phase": "searching",
            "sources_active": len(adapters),
            "sub_queries_count": len(sub_queries),
        })

        flat_results, source_errors, chunks, source_counts, sources_used = await self._fan_out_searches(
            adapters,
            sub_queries,
            config["max_results_per_source"],
            session_id=session_id,
        )

        counts_iter = (source_counts or dict(_aggregate_source_counts(flat_results))).items()
        for source_name, count in counts_iter:
            yield _sse_event("source_complete", {
                "source": source_name,
                "results_count": count,
            })

        if (sources_used or len(flat_results)) == 0:
            yield _sse_event("complete", {
                "session_id": session_id,
                "sources_used": 0,
                "citations": [],
                "errors": source_errors or None,
            })
            return

        # --- Step 3-4: Ingest + store (done locally or via Celery chord callback) ---
        if chunks is None:
            yield _sse_event("status", {
                "phase": "processing",
                "results_count": sources_used or len(flat_results),
            })
            chunks = await self._ingestion_pipeline.process(flat_results)

            if not chunks:
                yield _sse_event("complete", {
                    "session_id": session_id,
                    "sources_used": len(flat_results),
                    "citations": [],
                })
                return

            yield _sse_event("status", {"phase": "storing", "chunks_count": len(chunks)})
            collection_name = VectorStore.collection_name_for_session(session_id)
            upserted = await asyncio.to_thread(
                self._vector_store.upsert_chunks, collection_name, chunks,
            )
            logger.info("Stored %d chunks for session %s", upserted, session_id)
        else:
            # We can't stream worker-side progress; emit phases once to preserve
            # the frontend's expected phase sequence.
            yield _sse_event(
                "status",
                {"phase": "processing", "results_count": sources_used or len(flat_results)},
            )
            yield _sse_event("status", {"phase": "storing", "chunks_count": len(chunks)})

        # --- Step 5: Retrieve top-K via hybrid retrieval (BM25 + dense) ---
        yield _sse_event("status", {"phase": "retrieving"})
        relevant = await self._retriever.retrieve(
            query=query,
            session_id=session_id,
            chunks=chunks,
            top_k=config["retrieval_top_k"],
        )

        # --- Step 6: Stream synthesis via LLM ---
        yield _sse_event("status", {"phase": "synthesizing"})
        async for token in self._synthesizer.synthesize(query, relevant):
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
    ) -> tuple[list[SourceResult], list[str], list[Chunk] | None, dict[str, int] | None, int | None]:
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
    ) -> tuple[list[SourceResult], list[str], list[Chunk] | None, dict[str, int] | None, int | None]:
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
                adapter.name, query, exc,
            )
            return {"source": adapter.name, "results": [], "error": str(exc)}


def _aggregate_source_counts(results: list[SourceResult]) -> list[tuple[str, int]]:
    """Aggregate result counts by source name for ``source_complete`` events."""
    counts: dict[str, int] = {}
    for r in results:
        counts[r.source_name] = counts.get(r.source_name, 0) + 1
    return list(counts.items())
