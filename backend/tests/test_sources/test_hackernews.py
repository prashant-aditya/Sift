from __future__ import annotations

import httpx
import pytest
import respx

from app.sources.hackernews import HackerNewsAdapter, _ITEM_URL, _SEARCH_URL

pytestmark = pytest.mark.asyncio


@pytest.fixture
def adapter() -> HackerNewsAdapter:
    return HackerNewsAdapter()


def _algolia_response(n: int = 3, with_comments: bool = True) -> dict:
    hits = []
    for i in range(n):
        hits.append(
            {
                "objectID": str(1000 + i),
                "title": f"Story {i}",
                "url": f"https://example.com/story/{i}",
                "points": 100 - i * 10,
                "num_comments": 5 if with_comments else 0,
            }
        )
    return {"hits": hits}


def _item_response(story_id: str) -> dict:
    return {
        "id": int(story_id),
        "children": [
            {"text": f"Comment A on {story_id}", "points": 10},
            {"text": f"Comment B on {story_id}", "points": 5},
        ],
    }


class TestHackerNewsValidResponse:
    @respx.mock
    async def test_returns_source_results(self, adapter: HackerNewsAdapter):
        respx.get(_SEARCH_URL).mock(
            return_value=httpx.Response(200, json=_algolia_response(3))
        )
        for i in range(3):
            respx.get(f"{_ITEM_URL}/{1000 + i}").mock(
                return_value=httpx.Response(200, json=_item_response(str(1000 + i)))
            )

        results = await adapter.search("python")

        assert len(results) == 3
        assert results[0].title == "Story 0"
        assert results[0].source_name == "hackernews"
        assert results[0].metadata["points"] == 100

    @respx.mock
    async def test_fetches_comments_for_top_5(self, adapter: HackerNewsAdapter):
        respx.get(_SEARCH_URL).mock(
            return_value=httpx.Response(200, json=_algolia_response(7))
        )
        item_routes = []
        for i in range(7):
            route = respx.get(f"{_ITEM_URL}/{1000 + i}").mock(
                return_value=httpx.Response(200, json=_item_response(str(1000 + i)))
            )
            item_routes.append(route)

        results = await adapter.search("python", max_results=7)

        assert len(results) == 7
        for i in range(5):
            assert results[i].raw_content is not None
        for i in range(5, 7):
            assert results[i].raw_content is None

    @respx.mock
    async def test_respects_max_results(self, adapter: HackerNewsAdapter):
        respx.get(_SEARCH_URL).mock(
            return_value=httpx.Response(200, json=_algolia_response(2))
        )
        for i in range(2):
            respx.get(f"{_ITEM_URL}/{1000 + i}").mock(
                return_value=httpx.Response(200, json=_item_response(str(1000 + i)))
            )

        results = await adapter.search("test", max_results=2)
        assert len(results) == 2


class TestHackerNewsEmptyResults:
    @respx.mock
    async def test_no_hits(self, adapter: HackerNewsAdapter):
        respx.get(_SEARCH_URL).mock(
            return_value=httpx.Response(200, json={"hits": []})
        )

        results = await adapter.search("xyznonexistent123")
        assert results == []


class TestHackerNewsTimeout:
    @respx.mock
    async def test_returns_empty_on_timeout(self, adapter: HackerNewsAdapter):
        respx.get(_SEARCH_URL).mock(side_effect=httpx.ReadTimeout("timed out"))

        results = await adapter.search("timeout query")
        assert results == []


class TestHackerNewsMalformedResponse:
    @respx.mock
    async def test_missing_hits_key(self, adapter: HackerNewsAdapter):
        respx.get(_SEARCH_URL).mock(
            return_value=httpx.Response(200, json={"unexpected": "data"})
        )

        results = await adapter.search("malformed")
        assert results == []

    @respx.mock
    async def test_comment_fetch_failure_graceful(self, adapter: HackerNewsAdapter):
        respx.get(_SEARCH_URL).mock(
            return_value=httpx.Response(200, json=_algolia_response(1))
        )
        respx.get(f"{_ITEM_URL}/1000").mock(
            return_value=httpx.Response(500)
        )

        results = await adapter.search("error comments")
        assert len(results) == 1
        assert results[0].raw_content is None


class TestHackerNewsAvailability:
    def test_is_always_available(self, adapter: HackerNewsAdapter):
        assert adapter.is_available() is True
