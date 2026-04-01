from __future__ import annotations

import httpx
import pytest
import respx

from app.sources.arxiv import ArxivAdapter, _ARXIV_API


@pytest.fixture
def adapter(monkeypatch: pytest.MonkeyPatch) -> ArxivAdapter:
    monkeypatch.setattr("app.sources.arxiv._ARXIV_MIN_INTERVAL_SECONDS", 0.0)
    monkeypatch.setattr("app.sources.arxiv._arxiv_last_request_at", 0.0)
    return ArxivAdapter()


def _feed(entries: list[dict[str, str]]) -> str:
    entry_xml = []
    for e in entries:
        entry_xml.append(
            f"""
            <entry>
              <id>{e.get("id","")}</id>
              <title>{e.get("title","")}</title>
              <summary>{e.get("summary","")}</summary>
              <author><name>{e.get("author","")}</name></author>
              <published>{e.get("published","")}</published>
              <link title="pdf" rel="related" type="application/pdf" href="{e.get("pdf_url","")}" />
            </entry>
            """.strip()
        )
    return (
        """
        <feed xmlns="http://www.w3.org/2005/Atom">
          <title>ArXiv Query</title>
          {entries}
        </feed>
        """.replace("{entries}", "\n".join(entry_xml)).strip()
    )


class TestArxivValidResponse:
    @respx.mock
    async def test_returns_source_results(self, adapter: ArxivAdapter):
        xml = _feed(
            [
                {
                    "id": "http://arxiv.org/abs/1234.5678v1",
                    "title": "Test Paper",
                    "summary": "This is a summary.",
                    "author": "Ada Lovelace",
                    "published": "2024-01-01T00:00:00Z",
                    "pdf_url": "http://arxiv.org/pdf/1234.5678v1.pdf",
                }
            ]
        )
        respx.get(_ARXIV_API).mock(return_value=httpx.Response(200, text=xml))

        results = await adapter.search("transformers")

        assert len(results) == 1
        assert results[0].title == "Test Paper"
        assert results[0].url == "http://arxiv.org/abs/1234.5678v1"
        assert results[0].source_name == "arxiv"
        assert results[0].raw_content == "This is a summary."
        assert results[0].published_date is not None
        assert "Ada Lovelace" in results[0].metadata.get("authors", [])
        assert results[0].metadata.get("pdf_url") == "http://arxiv.org/pdf/1234.5678v1.pdf"

    @respx.mock
    async def test_respects_max_results(self, adapter: ArxivAdapter):
        xml = _feed(
            [
                {"id": "http://arxiv.org/abs/1", "title": "A", "summary": "S", "author": "A", "published": "2024-01-01T00:00:00Z", "pdf_url": "http://arxiv.org/pdf/1.pdf"},
                {"id": "http://arxiv.org/abs/2", "title": "B", "summary": "S", "author": "B", "published": "2024-01-01T00:00:00Z", "pdf_url": "http://arxiv.org/pdf/2.pdf"},
                {"id": "http://arxiv.org/abs/3", "title": "C", "summary": "S", "author": "C", "published": "2024-01-01T00:00:00Z", "pdf_url": "http://arxiv.org/pdf/3.pdf"},
            ]
        )
        route = respx.get(_ARXIV_API).mock(return_value=httpx.Response(200, text=xml))

        results = await adapter.search("llm", max_results=2)

        assert len(results) == 2
        assert route.called


class TestArxivEmptyAndErrors:
    @respx.mock
    async def test_malformed_xml_returns_empty(self, adapter: ArxivAdapter):
        respx.get(_ARXIV_API).mock(return_value=httpx.Response(200, text="<not xml"))
        assert await adapter.search("x") == []

    @respx.mock
    async def test_timeout_returns_empty(self, adapter: ArxivAdapter):
        respx.get(_ARXIV_API).mock(side_effect=httpx.ReadTimeout("timed out"))
        assert await adapter.search("x") == []

    @respx.mock
    async def test_429_retries_then_succeeds(self, adapter: ArxivAdapter, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr("app.sources.arxiv._ARXIV_MIN_INTERVAL_SECONDS", 0.0)
        respx.get(_ARXIV_API).mock(
            side_effect=[
                httpx.Response(429, headers={"Retry-After": "0"}),
                httpx.Response(200, text=_feed([])),
            ]
        )
        assert await adapter.search("x") == []

