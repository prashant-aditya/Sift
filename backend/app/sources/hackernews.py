from __future__ import annotations

import logging

import httpx

from app.sources.base import SourceAdapter, SourceResult

logger = logging.getLogger(__name__)

_SEARCH_URL = "https://hn.algolia.com/api/v1/search"
_ITEM_URL = "https://hn.algolia.com/api/v1/items"


class HackerNewsAdapter(SourceAdapter):
    """Searches Hacker News stories via the Algolia API.

    Rate-limit policy: 2 req/sec, burst 10.
    Fetches top stories by relevance and comments for the first 5 stories.
    """

    name = "hackernews"
    display_name = "Hacker News"
    max_results = 10
    timeout_seconds = 10

    _COMMENT_STORIES = 5

    def is_available(self) -> bool:
        return True

    async def search(
        self, query: str, max_results: int | None = None
    ) -> list[SourceResult]:
        limit = max_results or self.max_results
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                resp = await client.get(
                    _SEARCH_URL,
                    params={
                        "query": query,
                        "tags": "story",
                        "hitsPerPage": limit,
                    },
                )
                resp.raise_for_status()
                hits = resp.json().get("hits", [])
                return await self._build_results(client, hits, limit)
        except httpx.TimeoutException:
            logger.warning("HackerNews search timed out for query: %s", query)
            return []
        except Exception:
            logger.exception("HackerNews search failed for query: %s", query)
            return []

    async def _build_results(
        self,
        client: httpx.AsyncClient,
        hits: list[dict],
        limit: int,
    ) -> list[SourceResult]:
        results: list[SourceResult] = []
        for idx, hit in enumerate(hits[:limit]):
            story_id = hit.get("objectID", "")
            title = hit.get("title", "")
            url = hit.get("url") or f"https://news.ycombinator.com/item?id={story_id}"
            points = hit.get("points", 0)
            num_comments = hit.get("num_comments", 0)

            raw_content: str | None = None
            if idx < self._COMMENT_STORIES and num_comments > 0:
                raw_content = await self._fetch_top_comments(client, story_id)

            results.append(
                SourceResult(
                    title=title,
                    url=url,
                    snippet=f"{points} points | {num_comments} comments",
                    raw_content=raw_content,
                    source_name=self.name,
                    metadata={
                        "points": points,
                        "num_comments": num_comments,
                        "story_id": story_id,
                    },
                )
            )
        return results

    async def _fetch_top_comments(
        self, client: httpx.AsyncClient, story_id: str
    ) -> str | None:
        try:
            resp = await client.get(f"{_ITEM_URL}/{story_id}")
            if resp.status_code != 200:
                return None
            children = resp.json().get("children", [])
            comments_with_text = [c for c in children if c.get("text")]
            comments_with_text.sort(
                key=lambda c: c.get("points") or 0, reverse=True
            )
            texts = [c["text"] for c in comments_with_text[:5]]
            return "\n---\n".join(texts) if texts else None
        except Exception:
            return None
