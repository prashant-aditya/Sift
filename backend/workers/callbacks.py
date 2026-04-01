"""Celery chord callback for ingestion + vector upsert."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.config import get_settings
from app.db.vector_store import VectorStore
from app.ingestion.embedder import EmbeddingGenerator
from app.ingestion.pipeline import IngestionPipeline
from app.sources.base import SourceResult
from workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro):
    return asyncio.run(coro)


def _build_ingestion_pipeline() -> IngestionPipeline:
    settings = get_settings()
    embedder = EmbeddingGenerator(
        hf_api_token=settings.hf_api_token,
        model_name=settings.embedding_model,
    )
    return IngestionPipeline(embedder=embedder)


def _build_vector_store() -> VectorStore:
    return VectorStore()


@celery_app.task(name="workers.callbacks.process_results")
def process_results(  # type: ignore[no-untyped-def]
    search_outcomes: list[dict[str, Any]],
    *,
    session_id: str,
) -> dict[str, Any]:
    """Chord callback: dedup → chunk → embed → Chroma upsert.

    Returns:
      {
        "session_id": str,
        "flat_results": int,
        "sources_used": int,
        "chunks": list[dict],  # Chunk without embedding (JSON-safe)
        "errors": list[str] | None,
      }
    """
    errors: list[str] = []
    flat: list[SourceResult] = []
    source_counts: dict[str, int] = {}

    for out in search_outcomes or []:
        src = out.get("source", "unknown")
        err = out.get("error")
        if err:
            errors.append(f"{src}: {err}")

        for raw in out.get("results", []) or []:
            try:
                sr = SourceResult(**raw)
                flat.append(sr)
                source_counts[sr.source_name] = source_counts.get(sr.source_name, 0) + 1
            except Exception as exc:
                errors.append(f"{src}: invalid_result_payload ({exc})")

    if not flat:
        return {
            "session_id": session_id,
            "flat_results": 0,
            "sources_used": 0,
            "chunks": [],
            "source_counts": {},
            "errors": errors or None,
        }

    pipeline = _build_ingestion_pipeline()
    chunks = _run_async(pipeline.process(flat))

    if not chunks:
        return {
            "session_id": session_id,
            "flat_results": len(flat),
            "sources_used": len(flat),
            "chunks": [],
            "source_counts": source_counts,
            "errors": errors or None,
        }

    store = _build_vector_store()
    collection_name = VectorStore.collection_name_for_session(session_id)
    upserted = store.upsert_chunks(collection_name, chunks)
    logger.info("Chord callback upserted=%d session=%s", upserted, session_id)

    chunks_payload = [c.model_dump(exclude={"embedding"}) for c in chunks]
    return {
        "session_id": session_id,
        "flat_results": len(flat),
        "sources_used": len(flat),
        "chunks": chunks_payload,
        "source_counts": source_counts,
        "errors": errors or None,
    }
