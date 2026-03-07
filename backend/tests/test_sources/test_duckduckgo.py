from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from app.sources.duckduckgo import DuckDuckGoAdapter

pytestmark = pytest.mark.asyncio


@pytest.fixture
def adapter() -> DuckDuckGoAdapter:
    return DuckDuckGoAdapter()


def _make_raw_results(n: int = 3) -> list[dict]:
    return [
        {
            "title": f"Result {i}",
            "href": f"https://example.com/{i}",
            "body": f"Snippet for result {i}",
        }
        for i in range(n)
    ]


class TestDuckDuckGoValidResponse:
    async def test_returns_source_results(self, adapter: DuckDuckGoAdapter):
        mock_ddgs = MagicMock()
        mock_ddgs.text.return_value = _make_raw_results(3)

        with patch(
            "app.sources.duckduckgo.DDGS", return_value=mock_ddgs
        ):
            results = await adapter.search("python fastapi")

        assert len(results) == 3
        assert results[0].title == "Result 0"
        assert results[0].url == "https://example.com/0"
        assert results[0].source_name == "duckduckgo"

    async def test_respects_max_results(self, adapter: DuckDuckGoAdapter):
        mock_ddgs = MagicMock()
        mock_ddgs.text.return_value = _make_raw_results(2)

        with patch(
            "app.sources.duckduckgo.DDGS", return_value=mock_ddgs
        ):
            results = await adapter.search("test", max_results=2)

        mock_ddgs.text.assert_called_once_with("test", max_results=2)
        assert len(results) == 2


class TestDuckDuckGoEmptyResults:
    async def test_empty_list_from_api(self, adapter: DuckDuckGoAdapter):
        mock_ddgs = MagicMock()
        mock_ddgs.text.return_value = []

        with patch(
            "app.sources.duckduckgo.DDGS", return_value=mock_ddgs
        ):
            results = await adapter.search("obscure query xyz123")

        assert results == []


class TestDuckDuckGoTimeout:
    async def test_returns_empty_on_timeout(self, adapter: DuckDuckGoAdapter):
        adapter.timeout_seconds = 0.01

        def _slow_search(*_a, **_kw):
            import time
            time.sleep(5)
            return []

        mock_ddgs = MagicMock()
        mock_ddgs.text.side_effect = _slow_search

        with patch(
            "app.sources.duckduckgo.DDGS", return_value=mock_ddgs
        ):
            results = await adapter.search("timeout query")

        assert results == []


class TestDuckDuckGoMalformedResponse:
    async def test_missing_keys(self, adapter: DuckDuckGoAdapter):
        mock_ddgs = MagicMock()
        mock_ddgs.text.return_value = [{"unexpected": "data"}]

        with patch(
            "app.sources.duckduckgo.DDGS", return_value=mock_ddgs
        ):
            results = await adapter.search("malformed")

        assert len(results) == 1
        assert results[0].title == ""
        assert results[0].url == ""

    async def test_exception_returns_empty(self, adapter: DuckDuckGoAdapter):
        mock_ddgs = MagicMock()
        mock_ddgs.text.side_effect = RuntimeError("API broke")

        with patch(
            "app.sources.duckduckgo.DDGS", return_value=mock_ddgs
        ):
            results = await adapter.search("error query")

        assert results == []


class TestDuckDuckGoAvailability:
    def test_is_always_available(self, adapter: DuckDuckGoAdapter):
        assert adapter.is_available() is True
