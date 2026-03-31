"""Celery tasks for source search fan-out."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.sources.base import SourceResult
from app.sources.duckduckgo import DuckDuckGoAdapter
from app.sources.hackernews import HackerNewsAdapter
from app.sources.registry import SourceRegistry
from app.sources.wikipedia import WikipediaAdapter
from workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def _build_source_registry() -> SourceRegistry:
    registry = SourceRegistry()
    registry.register(DuckDuckGoAdapter())
    registry.register(WikipediaAdapter())
    registry.register(HackerNewsAdapter())
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
        registry = _build_source_registry()
        adapter = registry.get(source_name)
        if adapter is None or not adapter.is_available():
            return {"source": source_name, "results": [], "error": "source_not_available"}

        all_results: list[SourceResult] = []
        for q in sub_queries:
            results = _run_async(adapter.search(q, max_results=max_results))
            all_results.extend(results)

        payload = [r.model_dump() for r in all_results]
        return {"source": source_name, "results": payload, "error": None}
    except Exception as exc:
        logger.exception("search_source failed source=%s", source_name)
        try:
            raise self.retry(exc=exc)
        except Exception:
            # On final failure Celery raises; return a structured error for safety
            # (not typically reached when retries are exhausted).
            return {"source": source_name, "results": [], "error": str(exc)}

