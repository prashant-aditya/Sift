"""End-to-end tests for IngestionPipeline with mock data."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.ingestion.chunker import TextChunker
from app.ingestion.embedder import DIMENSIONS, EmbeddingGenerator
from app.ingestion.pipeline import IngestionPipeline
from app.sources.base import SourceResult


def _make_source_result(
    *,
    title: str = "Test Article",
    url: str = "https://example.com/test",
    snippet: str = "A short snippet.",
    raw_content: str | None = None,
    source_name: str = "test_source",
) -> SourceResult:
    return SourceResult(
        title=title,
        url=url,
        snippet=snippet,
        raw_content=raw_content,
        source_name=source_name,
        published_date=datetime(2025, 6, 1, tzinfo=timezone.utc),
    )


def _fake_embedder() -> EmbeddingGenerator:
    """Return an embedder whose ``embed`` is an AsyncMock."""
    embedder = EmbeddingGenerator(hf_api_token="")
    mock_embed = AsyncMock(
        side_effect=lambda texts: [[0.1] * DIMENSIONS for _ in texts]
    )
    embedder.embed = mock_embed  # type: ignore[assignment]
    return embedder


class TestPipelineExtraction:
    @pytest.mark.asyncio
    async def test_uses_raw_html_when_available(self):
        html = "<html><body><p>Full article content from the web.</p></body></html>"
        result = _make_source_result(raw_content=html)
        pipeline = IngestionPipeline(embedder=_fake_embedder())
        chunks = await pipeline.process([result])
        assert len(chunks) >= 1
        assert "Full article content" in chunks[0].text

    @pytest.mark.asyncio
    async def test_uses_raw_text_when_no_html(self):
        result = _make_source_result(raw_content="Plain text content here.")
        pipeline = IngestionPipeline(embedder=_fake_embedder())
        chunks = await pipeline.process([result])
        assert len(chunks) >= 1
        assert "Plain text content" in chunks[0].text

    @pytest.mark.asyncio
    async def test_falls_back_to_snippet(self):
        result = _make_source_result(snippet="Snippet-only result.")
        pipeline = IngestionPipeline(embedder=_fake_embedder())
        chunks = await pipeline.process([result])
        assert len(chunks) >= 1
        assert "Snippet-only result" in chunks[0].text


class TestPipelineChunking:
    @pytest.mark.asyncio
    async def test_long_text_produces_multiple_chunks(self):
        long_text = " ".join(["information"] * 2000)
        result = _make_source_result(raw_content=long_text)
        pipeline = IngestionPipeline(embedder=_fake_embedder())
        chunks = await pipeline.process([result])
        assert len(chunks) > 1

    @pytest.mark.asyncio
    async def test_chunk_size_within_tolerance(self):
        long_text = " ".join(["knowledge"] * 2000)
        result = _make_source_result(raw_content=long_text)
        chunker = TextChunker(chunk_size=512, chunk_overlap=64)
        pipeline = IngestionPipeline(chunker=chunker, embedder=_fake_embedder())
        chunks = await pipeline.process([result])
        for c in chunks:
            token_count = chunker.token_count(c.text)
            tolerance = int(512 * 1.15)
            assert token_count <= tolerance, (
                f"Chunk {c.chunk_index} has {token_count} tokens (max {tolerance})"
            )


class TestPipelineMetadata:
    @pytest.mark.asyncio
    async def test_metadata_preserved_through_pipeline(self):
        result = _make_source_result(
            title="My Title",
            url="https://example.com/page",
            source_name="wiki",
            raw_content="Some content to chunk.",
        )
        pipeline = IngestionPipeline(embedder=_fake_embedder())
        chunks = await pipeline.process([result])
        assert len(chunks) >= 1
        c = chunks[0]
        assert c.source_url == "https://example.com/page"
        assert c.source_name == "wiki"
        assert c.source_title == "My Title"
        assert c.published_date == datetime(2025, 6, 1, tzinfo=timezone.utc)

    @pytest.mark.asyncio
    async def test_multiple_sources_produce_chunks(self):
        results = [
            _make_source_result(title="Article A", raw_content="Content from A."),
            _make_source_result(title="Article B", raw_content="Content from B."),
        ]
        pipeline = IngestionPipeline(embedder=_fake_embedder())
        chunks = await pipeline.process(results)
        titles = {c.source_title for c in chunks}
        assert "Article A" in titles
        assert "Article B" in titles


class TestPipelineEmbeddings:
    @pytest.mark.asyncio
    async def test_every_chunk_has_embedding(self):
        result = _make_source_result(raw_content="Some text to embed into vectors.")
        pipeline = IngestionPipeline(embedder=_fake_embedder())
        chunks = await pipeline.process([result])
        for c in chunks:
            assert c.embedding is not None
            assert len(c.embedding) == DIMENSIONS

    @pytest.mark.asyncio
    async def test_embedder_called_with_all_chunk_texts(self):
        embedder = _fake_embedder()
        long_text = " ".join(["data"] * 2000)
        result = _make_source_result(raw_content=long_text)
        pipeline = IngestionPipeline(embedder=embedder)
        chunks = await pipeline.process([result])
        call_args = embedder.embed.call_args  # type: ignore[union-attr]
        passed_texts = call_args[0][0]
        assert len(passed_texts) == len(chunks)


class TestPipelineEdgeCases:
    @pytest.mark.asyncio
    async def test_empty_source_results(self):
        pipeline = IngestionPipeline(embedder=_fake_embedder())
        assert await pipeline.process([]) == []

    @pytest.mark.asyncio
    async def test_source_with_empty_content(self):
        result = _make_source_result(snippet="", raw_content="")
        pipeline = IngestionPipeline(embedder=_fake_embedder())
        chunks = await pipeline.process([result])
        assert chunks == []


class TestPipelineDeduplication:
    @pytest.mark.asyncio
    async def test_deduplicates_before_embedding_using_authority(self):
        pytest.importorskip("datasketch")
        # Two identical documents; wikipedia should win over duckduckgo.
        content = (
            "Sift runs extraction then deduplication then chunking then embedding "
            "to reduce redundant documents."
        )
        wiki = _make_source_result(
            title="Wiki Title",
            url="https://example.com/wiki",
            source_name="wikipedia",
            raw_content=content,
        )
        ddg = _make_source_result(
            title="DDG Title",
            url="https://example.com/ddg",
            source_name="duckduckgo",
            raw_content=content,
        )

        embedder = _fake_embedder()
        pipeline = IngestionPipeline(embedder=embedder)
        chunks = await pipeline.process([ddg, wiki])

        assert chunks
        assert {c.source_name for c in chunks} == {"wikipedia"}
        assert {c.source_title for c in chunks} == {"Wiki Title"}
