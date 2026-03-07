from __future__ import annotations

import httpx
import pytest
import respx

from app.sources.wikipedia import WikipediaAdapter, _SEARCH_API, _SUMMARY_API

pytestmark = pytest.mark.asyncio


@pytest.fixture
def adapter() -> WikipediaAdapter:
    return WikipediaAdapter()


def _search_response(titles: list[str]) -> dict:
    return {
        "query": {
            "search": [{"title": t} for t in titles],
        }
    }


def _summary_response(title: str) -> dict:
    return {
        "title": title,
        "description": f"Short description of {title}",
        "extract": f"Full extract text for {title}. This is the article content.",
        "content_urls": {
            "desktop": {"page": f"https://en.wikipedia.org/wiki/{title}"}
        },
    }


class TestWikipediaValidResponse:
    @respx.mock
    async def test_returns_source_results(self, adapter: WikipediaAdapter):
        respx.get(_SEARCH_API).mock(
            return_value=httpx.Response(200, json=_search_response(["Python_(programming_language)"]))
        )
        respx.get(f"{_SUMMARY_API}/Python_(programming_language)").mock(
            return_value=httpx.Response(200, json=_summary_response("Python (programming language)"))
        )

        results = await adapter.search("python programming")

        assert len(results) == 1
        assert results[0].title == "Python (programming language)"
        assert results[0].source_name == "wikipedia"
        assert results[0].raw_content is not None
        assert "Full extract text" in results[0].raw_content

    @respx.mock
    async def test_multiple_results(self, adapter: WikipediaAdapter):
        titles = ["FastAPI", "Flask_(web_framework)", "Django_(web_framework)"]
        respx.get(_SEARCH_API).mock(
            return_value=httpx.Response(200, json=_search_response(titles))
        )
        for t in titles:
            respx.get(f"{_SUMMARY_API}/{t}").mock(
                return_value=httpx.Response(200, json=_summary_response(t))
            )

        results = await adapter.search("python web frameworks", max_results=3)
        assert len(results) == 3


class TestWikipediaEmptyResults:
    @respx.mock
    async def test_no_search_hits(self, adapter: WikipediaAdapter):
        respx.get(_SEARCH_API).mock(
            return_value=httpx.Response(200, json={"query": {"search": []}})
        )

        results = await adapter.search("xyznonexistent123")
        assert results == []


class TestWikipediaTimeout:
    @respx.mock
    async def test_returns_empty_on_timeout(self, adapter: WikipediaAdapter):
        respx.get(_SEARCH_API).mock(side_effect=httpx.ReadTimeout("timed out"))

        results = await adapter.search("timeout query")
        assert results == []


class TestWikipediaMalformedResponse:
    @respx.mock
    async def test_missing_query_key(self, adapter: WikipediaAdapter):
        respx.get(_SEARCH_API).mock(
            return_value=httpx.Response(200, json={"unexpected": "data"})
        )

        results = await adapter.search("malformed")
        assert results == []

    @respx.mock
    async def test_summary_404_skipped(self, adapter: WikipediaAdapter):
        respx.get(_SEARCH_API).mock(
            return_value=httpx.Response(200, json=_search_response(["GoodArticle", "Missing"]))
        )
        respx.get(f"{_SUMMARY_API}/GoodArticle").mock(
            return_value=httpx.Response(200, json=_summary_response("GoodArticle"))
        )
        respx.get(f"{_SUMMARY_API}/Missing").mock(
            return_value=httpx.Response(404)
        )

        results = await adapter.search("mixed results")
        assert len(results) == 1
        assert results[0].title == "GoodArticle"


class TestWikipediaAvailability:
    def test_is_always_available(self, adapter: WikipediaAdapter):
        assert adapter.is_available() is True
