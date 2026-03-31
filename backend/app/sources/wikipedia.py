from __future__ import annotations

import logging
from typing import Optional

import httpx

from app.sources.base import SourceAdapter, SourceResult

logger = logging.getLogger(__name__)

_SEARCH_API = "https://en.wikipedia.org/w/api.php"
_SUMMARY_API = "https://en.wikipedia.org/api/rest_v1/page/summary"


class WikipediaAdapter(SourceAdapter):
    """Fetches article summaries via the Wikipedia REST + search APIs.

    Rate-limit policy: 5 req/sec, burst 20.
    Default max_results: 3 (top 3 article summaries).
    """

    name = "wikipedia"
    display_name = "Wikipedia"
    max_results = 3
    timeout_seconds = 10

    def is_available(self) -> bool:
        return True

    async def search(
        self, query: str, max_results: Optional[int] = None
    ) -> list[SourceResult]:
        limit = max_results or self.max_results
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                titles = await self._search_titles(client, query, limit)
                return await self._fetch_summaries(client, titles)
        except httpx.TimeoutException:
            logger.warning("Wikipedia search timed out for query: %s", query)
            return []
        except Exception:
            logger.exception("Wikipedia search failed for query: %s", query)
            return []

    async def _search_titles(
        self, client: httpx.AsyncClient, query: str, limit: int
    ) -> list[str]:
        resp = await client.get(
            _SEARCH_API,
            params={
                "action": "query",
                "list": "search",
                "srsearch": query,
                "srlimit": limit,
                "format": "json",
            },
        )
        resp.raise_for_status()
        hits = resp.json().get("query", {}).get("search", [])
        return [h["title"] for h in hits]

    async def _fetch_summaries(
        self, client: httpx.AsyncClient, titles: list[str]
    ) -> list[SourceResult]:
        results: list[SourceResult] = []
        for title in titles:
            resp = await client.get(f"{_SUMMARY_API}/{title}")
            if resp.status_code != 200:
                continue
            data = resp.json()
            page_url = (
                data.get("content_urls", {})
                .get("desktop", {})
                .get("page", f"https://en.wikipedia.org/wiki/{title}")
            )
            results.append(
                SourceResult(
                    title=data.get("title", title),
                    url=page_url,
                    snippet=data.get("description", ""),
                    raw_content=data.get("extract"),
                    source_name=self.name,
                )
            )
        return results
