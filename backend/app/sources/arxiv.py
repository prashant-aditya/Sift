from __future__ import annotations

import logging
import time
from asyncio import sleep
from asyncio import Lock
from datetime import datetime, timezone
from typing import Optional

import feedparser
import httpx

from app.sources.base import SourceAdapter, SourceResult

logger = logging.getLogger(__name__)

_ARXIV_API = "https://export.arxiv.org/api/query"
_ARXIV_HEADERS = {
    "User-Agent": "SiftResearchEngine/0.1 (contact@example.com)",
    "Accept": "application/atom+xml",
}

_ARXIV_MIN_INTERVAL_SECONDS = 3.0  # 1 request per 3 seconds
_arxiv_rate_lock = Lock()
_arxiv_last_request_at = 0.0


async def _arxiv_throttle() -> None:
    global _arxiv_last_request_at
    async with _arxiv_rate_lock:
        now = time.monotonic()
        wait_for = _ARXIV_MIN_INTERVAL_SECONDS - (now - _arxiv_last_request_at)
        if wait_for > 0:
            await sleep(wait_for)
        _arxiv_last_request_at = time.monotonic()

class ArxivAdapter(SourceAdapter):
    """Searches ArXiv papers via the public Atom API (no key required).

    Rate-limit policy: 1 request per 3 seconds.
    """

    name = "arxiv"
    display_name = "ArXiv"
    max_results = 5
    timeout_seconds = 10

    def is_available(self) -> bool:
        return True

    async def search(self, query: str, max_results: Optional[int] = None) -> list[SourceResult]:
        limit = max_results or self.max_results
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds, headers=_ARXIV_HEADERS) as client:
                await _arxiv_throttle()
                resp = await client.get(
                    _ARXIV_API,
                    params={
                        "search_query": f"all:{query}",
                        "start": 0,
                        "max_results": int(limit),
                        "sortBy": "relevance",
                        "sortOrder": "descending",
                    },
                )
                if resp.status_code == 429:
                    retry_after = float(resp.headers.get("Retry-After") or 3)
                    await sleep(max(retry_after, _ARXIV_MIN_INTERVAL_SECONDS))
                    await _arxiv_throttle()
                    resp = await client.get(
                        _ARXIV_API,
                        params={
                            "search_query": f"all:{query}",
                            "start": 0,
                            "max_results": int(limit),
                            "sortBy": "relevance",
                            "sortOrder": "descending",
                        },
                    )
                resp.raise_for_status()
                return self._parse_feed(resp.text)[: int(limit)]
        except httpx.TimeoutException:
            logger.warning("ArXiv search timed out for query: %s", query)
            return []
        except Exception:
            logger.exception("ArXiv search failed for query: %s", query)
            return []

    def _parse_feed(self, xml_text: str) -> list[SourceResult]:
        parsed = feedparser.parse(xml_text)
        if getattr(parsed, "bozo", 0):
            return []

        results: list[SourceResult] = []
        for entry in getattr(parsed, "entries", []) or []:
            title = str(getattr(entry, "title", "") or "").strip()
            summary = str(getattr(entry, "summary", "") or "").strip()

            url = str(getattr(entry, "id", "") or "").strip()
            if not url:
                url = str(getattr(entry, "link", "") or "").strip()

            published_raw = str(getattr(entry, "published", "") or "").strip()
            published_date: datetime | None = None
            if published_raw:
                try:
                    published_date = datetime.fromisoformat(published_raw.replace("Z", "+00:00")).astimezone(
                        timezone.utc
                    )
                except Exception:
                    published_date = None

            authors: list[str] = []
            for a in getattr(entry, "authors", []) or []:
                name = str((a or {}).get("name") or "").strip() if isinstance(a, dict) else str(getattr(a, "name", "") or "").strip()
                if name:
                    authors.append(name)

            pdf_url = ""
            for link in getattr(entry, "links", []) or []:
                if not isinstance(link, dict):
                    continue
                href = str(link.get("href") or "").strip()
                if not href:
                    continue
                link_type = str(link.get("type") or "").lower()
                title_hint = str(link.get("title") or "").lower()
                rel = str(link.get("rel") or "").lower()
                if link_type == "application/pdf" or "pdf" in title_hint or (rel == "related" and "pdf" in href):
                    pdf_url = href
                    break

            results.append(
                SourceResult(
                    title=title,
                    url=url,
                    snippet=(summary[:240] + "…") if len(summary) > 240 else summary,
                    raw_content=summary or None,
                    source_name=self.name,
                    published_date=published_date,
                    metadata={
                        "authors": authors,
                        "pdf_url": pdf_url,
                    },
                )
            )

        return results

