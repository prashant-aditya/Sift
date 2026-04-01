from __future__ import annotations

import httpx
import pytest
import respx

from app.sources.reddit import RedditAdapter, _REDDIT_SEARCH


@pytest.fixture
def adapter(monkeypatch: pytest.MonkeyPatch) -> RedditAdapter:
    monkeypatch.setattr("app.sources.reddit._REDDIT_MIN_INTERVAL_SECONDS", 0.0)
    monkeypatch.setattr("app.sources.reddit._reddit_last_request_at", 0.0)
    return RedditAdapter()


def _search_payload(children: list[dict]) -> dict:
    return {"data": {"children": [{"data": c} for c in children]}}


class TestRedditValidResponse:
    @respx.mock
    async def test_returns_source_results(self, adapter: RedditAdapter):
        permalink = "/r/test/comments/abc123/post_title/"
        comments_url = f"https://www.reddit.com{permalink}.json"
        respx.get(_REDDIT_SEARCH).mock(
            return_value=httpx.Response(
                200,
                json=_search_payload(
                    [
                        {
                            "title": "Post title",
                            "permalink": permalink,
                            "subreddit": "test",
                            "score": 42,
                            "num_comments": 7,
                            "selftext": "Post body",
                        }
                    ]
                ),
            )
        )
        respx.get(comments_url).mock(
            return_value=httpx.Response(
                200,
                json=[
                    {"data": {"children": []}},
                    {
                        "data": {
                            "children": [
                                {
                                    "kind": "t1",
                                    "data": {"body": "Comment A", "score": 10},
                                },
                                {
                                    "kind": "t1",
                                    "data": {"body": "Comment B", "score": 5},
                                },
                                {
                                    "kind": "t1",
                                    "data": {"body": "Comment C", "score": 99},
                                },
                            ]
                        }
                    },
                ],
            )
        )

        results = await adapter.search("fastapi")

        assert len(results) == 1
        assert results[0].title == "Post title"
        assert results[0].url.startswith("https://www.reddit.com/r/test/comments/")
        assert results[0].source_name == "reddit"
        assert "Post body" in (results[0].raw_content or "")
        assert "Comment C" in (results[0].raw_content or "")
        assert results[0].metadata["subreddit"] == "test"

    @respx.mock
    async def test_respects_max_results(self, adapter: RedditAdapter):
        route = respx.get(_REDDIT_SEARCH).mock(
            return_value=httpx.Response(
                200,
                json=_search_payload(
                    [
                        {
                            "title": "A",
                            "permalink": "/r/a/comments/1/a/",
                            "subreddit": "a",
                            "score": 1,
                            "num_comments": 1,
                        },
                        {
                            "title": "B",
                            "permalink": "/r/b/comments/2/b/",
                            "subreddit": "b",
                            "score": 1,
                            "num_comments": 1,
                        },
                        {
                            "title": "C",
                            "permalink": "/r/c/comments/3/c/",
                            "subreddit": "c",
                            "score": 1,
                            "num_comments": 1,
                        },
                    ]
                ),
            )
        )

        results = await adapter.search("x", max_results=2)
        assert len(results) == 2
        assert route.called


class TestRedditEmptyAndErrors:
    @respx.mock
    async def test_empty_children_returns_empty(self, adapter: RedditAdapter):
        respx.get(_REDDIT_SEARCH).mock(
            return_value=httpx.Response(200, json=_search_payload([]))
        )
        assert await adapter.search("x") == []

    @respx.mock
    async def test_timeout_returns_empty(self, adapter: RedditAdapter):
        respx.get(_REDDIT_SEARCH).mock(side_effect=httpx.ReadTimeout("timed out"))
        assert await adapter.search("x") == []

    @respx.mock
    async def test_429_retries_then_succeeds(
        self, adapter: RedditAdapter, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr("app.sources.reddit._REDDIT_MIN_INTERVAL_SECONDS", 0.0)
        respx.get(_REDDIT_SEARCH).mock(
            side_effect=[
                httpx.Response(429, headers={"Retry-After": "0"}),
                httpx.Response(200, json=_search_payload([])),
            ]
        )
        assert await adapter.search("x") == []
