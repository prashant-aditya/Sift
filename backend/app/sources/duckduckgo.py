from __future__ import annotations

import asyncio
import logging

from duckduckgo_search import DDGS

from app.sources.base import SourceAdapter, SourceResult

logger = logging.getLogger(__name__)


class DuckDuckGoAdapter(SourceAdapter):
    """Web search via the DuckDuckGo Instant Answer API (no key required).

    Rate-limit policy: 1 req/sec, burst 5.
    Hard timeout: 10 s.
    """

    name = "duckduckgo"
    display_name = "DuckDuckGo Web Search"
    max_results = 10
    timeout_seconds = 10

    _RATE_LIMIT_DELAY = 1.0

    def is_available(self) -> bool:
        return True

    async def search(
        self, query: str, max_results: int | None = None
    ) -> list[SourceResult]:
        limit = max_results or self.max_results
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(self._sync_search, query, limit),
                timeout=self.timeout_seconds,
            )
        except asyncio.TimeoutError:
            logger.warning("DuckDuckGo search timed out for query: %s", query)
            return []
        except Exception:
            logger.exception("DuckDuckGo search failed for query: %s", query)
            return []

    def _sync_search(self, query: str, max_results: int) -> list[SourceResult]:
        raw = DDGS().text(query, max_results=max_results)

        results: list[SourceResult] = []
        for item in raw:
            results.append(
                SourceResult(
                    title=item.get("title", ""),
                    url=item.get("href", ""),
                    snippet=item.get("body", ""),
                    raw_content=item.get("body"),
                    source_name=self.name,
                )
            )

        return results
