from __future__ import annotations

import logging
import time
from asyncio import Lock, sleep
from typing import Optional

import httpx

from app.sources.base import SourceAdapter, SourceResult

logger = logging.getLogger(__name__)

_REDDIT_SEARCH = "https://www.reddit.com/search.json"
_REDDIT_HEADERS = {
    # Reddit requires a descriptive UA; anonymous requests can be rate-limited.
    "User-Agent": "SiftResearchEngine/0.1 (contact@example.com)",
    "Accept": "application/json",
}

_TARGET_SUBREDDITS = [
    "programming",
    "devops",
    "machinelearning",
    "Python",
    "ExperiencedDevs",
]

_REDDIT_MIN_INTERVAL_SECONDS = 2.0  # 1 request per 2 seconds
_reddit_rate_lock = Lock()
_reddit_last_request_at = 0.0


async def _reddit_throttle() -> None:
    global _reddit_last_request_at
    async with _reddit_rate_lock:
        now = time.monotonic()
        wait_for = _REDDIT_MIN_INTERVAL_SECONDS - (now - _reddit_last_request_at)
        if wait_for > 0:
            await sleep(wait_for)
        _reddit_last_request_at = time.monotonic()


def _subreddit_scoped_query(query: str) -> str:
    scoped = " OR ".join([f"subreddit:{s}" for s in _TARGET_SUBREDDITS])
    return f"({query}) ({scoped})"


def _comments_url(permalink: str) -> str:
    if not permalink:
        return ""
    path = permalink if permalink.startswith("/") else f"/{permalink}"
    return f"https://www.reddit.com{path}.json"


def _extract_top_comments(payload: object, max_comments: int = 5) -> list[str]:
    if not isinstance(payload, list) or len(payload) < 2:
        return []
    comments_listing = payload[1]
    if not isinstance(comments_listing, dict):
        return []
    children = (comments_listing.get("data") or {}).get("children") or []
    if not isinstance(children, list):
        return []

    comments: list[tuple[int, str]] = []
    for c in children:
        if not isinstance(c, dict) or c.get("kind") != "t1":
            continue
        data = c.get("data")
        if not isinstance(data, dict):
            continue
        body = str(data.get("body") or "").strip()
        if not body:
            continue
        score = int(data.get("score") or 0)
        comments.append((score, body))

    comments.sort(key=lambda t: t[0], reverse=True)
    return [t[1] for t in comments[:max_comments]]


class RedditAdapter(SourceAdapter):
    """Searches Reddit posts via the public JSON endpoint (no auth).

    Rate-limit policy: 1 request per 2 seconds.
    """

    name = "reddit"
    display_name = "Reddit"
    max_results = 5
    timeout_seconds = 10

    def is_available(self) -> bool:
        return True

    async def search(
        self, query: str, max_results: Optional[int] = None
    ) -> list[SourceResult]:
        limit = max_results or self.max_results
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds, headers=_REDDIT_HEADERS
            ) as client:
                await _reddit_throttle()
                resp = await client.get(
                    _REDDIT_SEARCH,
                    params={
                        "q": _subreddit_scoped_query(query),
                        "limit": int(limit),
                        "sort": "relevance",
                        "t": "all",
                        "include_over_18": "on",
                        "raw_json": 1,
                    },
                )
                if resp.status_code == 429:
                    retry_after = float(resp.headers.get("Retry-After") or 2)
                    await sleep(max(retry_after, _REDDIT_MIN_INTERVAL_SECONDS))
                    await _reddit_throttle()
                    resp = await client.get(
                        _REDDIT_SEARCH,
                        params={
                            "q": _subreddit_scoped_query(query),
                            "limit": int(limit),
                            "sort": "relevance",
                            "t": "all",
                            "include_over_18": "on",
                            "raw_json": 1,
                        },
                    )
                resp.raise_for_status()
                payload = resp.json()
                children = ((payload or {}).get("data") or {}).get("children") or []
                if not isinstance(children, list):
                    return []

                results: list[SourceResult] = []
                for child in children[:limit]:
                    data = (
                        (child or {}).get("data") if isinstance(child, dict) else None
                    )
                    if not isinstance(data, dict):
                        continue

                    title = str(data.get("title") or "")
                    permalink = str(data.get("permalink") or "")
                    url = (
                        f"https://www.reddit.com{permalink}"
                        if permalink
                        else str(data.get("url") or "")
                    )
                    subreddit = str(data.get("subreddit") or "")
                    score = int(data.get("score") or 0)
                    num_comments = int(data.get("num_comments") or 0)
                    selftext = str(data.get("selftext") or "")

                    snippet = f"r/{subreddit} | {score} score | {num_comments} comments".strip()
                    raw_content_parts: list[str] = []
                    if selftext:
                        raw_content_parts.append(selftext)

                    comments_text: Optional[str] = None
                    comments_endpoint = _comments_url(permalink)
                    if comments_endpoint:
                        try:
                            await _reddit_throttle()
                            comments_resp = await client.get(
                                comments_endpoint,
                                params={"raw_json": 1, "sort": "top", "limit": 20},
                            )
                            if comments_resp.status_code == 429:
                                retry_after = float(
                                    comments_resp.headers.get("Retry-After") or 2
                                )
                                await sleep(
                                    max(retry_after, _REDDIT_MIN_INTERVAL_SECONDS)
                                )
                                await _reddit_throttle()
                                comments_resp = await client.get(
                                    comments_endpoint,
                                    params={"raw_json": 1, "sort": "top", "limit": 20},
                                )
                            if comments_resp.status_code == 200:
                                top_comments = _extract_top_comments(
                                    comments_resp.json(), max_comments=5
                                )
                                if top_comments:
                                    comments_text = "\n---\n".join(top_comments)
                        except Exception:
                            comments_text = None

                    if comments_text:
                        raw_content_parts.append(comments_text)

                    raw_content = (
                        "\n\nTop comments:\n".join(raw_content_parts)
                        if raw_content_parts
                        else None
                    )

                    results.append(
                        SourceResult(
                            title=title,
                            url=url,
                            snippet=snippet,
                            raw_content=raw_content,
                            source_name=self.name,
                            metadata={
                                "subreddit": subreddit,
                                "score": score,
                                "num_comments": num_comments,
                                "target_subreddits": _TARGET_SUBREDDITS,
                            },
                        )
                    )

                return results
        except httpx.TimeoutException:
            logger.warning("Reddit search timed out for query: %s", query)
            return []
        except Exception:
            logger.exception("Reddit search failed for query: %s", query)
            return []
