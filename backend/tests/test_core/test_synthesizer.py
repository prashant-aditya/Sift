"""Tests for app.core.synthesizer — cited answer generation via Groq."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.synthesizer import (
    NO_SOURCES_RESPONSE,
    Synthesizer,
    build_citation_map,
    _build_user_message,
)
from app.db.vector_store import RetrievedChunk
from app.ingestion.chunker import Chunk


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_chunk(
    *,
    text: str = "sample text",
    source_name: str = "wikipedia",
    source_title: str = "Test Article",
    source_url: str = "https://example.com",
    chunk_id: str = "abc12345-0000-0000-0000-000000000000",
    score: float = 0.95,
) -> RetrievedChunk:
    return RetrievedChunk(
        chunk=Chunk(
            chunk_id=chunk_id,
            text=text,
            source_url=source_url,
            source_name=source_name,
            source_title=source_title,
            chunk_index=0,
            total_chunks=1,
            fetched_at=datetime.now(timezone.utc),
        ),
        score=score,
        citation_id=f"{source_name}:{chunk_id[:8]}",
    )


@pytest.fixture()
def sample_chunks() -> list[RetrievedChunk]:
    return [
        _make_chunk(
            text="Kafka uses a distributed commit log.",
            source_name="wikipedia",
            source_title="Apache Kafka",
            source_url="https://en.wikipedia.org/wiki/Apache_Kafka",
            chunk_id="chunk-001",
        ),
        _make_chunk(
            text="RabbitMQ implements AMQP protocol.",
            source_name="hackernews",
            source_title="RabbitMQ Overview",
            source_url="https://news.ycombinator.com/item?id=999",
            chunk_id="chunk-002",
        ),
        _make_chunk(
            text="Kafka outperforms RabbitMQ at high throughput.",
            source_name="duckduckgo",
            source_title="Kafka vs RabbitMQ Benchmark",
            source_url="https://example.com/benchmark",
            chunk_id="chunk-003",
        ),
    ]


@pytest.fixture()
def synthesizer():
    with patch.dict("os.environ", {"GROQ_API_KEY": "test-key"}):
        return Synthesizer(api_key="test-key")


# ---------------------------------------------------------------------------
# _build_user_message tests
# ---------------------------------------------------------------------------

class TestBuildUserMessage:
    def test_contains_numbered_sources(self, sample_chunks: list[RetrievedChunk]):
        msg = _build_user_message("Kafka vs RabbitMQ", sample_chunks)

        assert "[1]" in msg
        assert "[2]" in msg
        assert "[3]" in msg
        assert "Kafka uses a distributed commit log." in msg
        assert "RabbitMQ implements AMQP protocol." in msg

    def test_contains_query(self, sample_chunks: list[RetrievedChunk]):
        msg = _build_user_message("my research question", sample_chunks)
        assert "Query: my research question" in msg

    def test_contains_source_metadata(self, sample_chunks: list[RetrievedChunk]):
        msg = _build_user_message("test", sample_chunks)
        assert "wikipedia" in msg
        assert "Apache Kafka" in msg


# ---------------------------------------------------------------------------
# build_citation_map tests
# ---------------------------------------------------------------------------

class TestBuildCitationMap:
    def test_maps_chunks_to_numeric_ids(self, sample_chunks: list[RetrievedChunk]):
        mappings = build_citation_map(sample_chunks)

        assert len(mappings) == 3
        assert mappings[0].citation_id == 1
        assert mappings[1].citation_id == 2
        assert mappings[2].citation_id == 3

    def test_preserves_source_metadata(self, sample_chunks: list[RetrievedChunk]):
        mappings = build_citation_map(sample_chunks)

        assert mappings[0].source_name == "wikipedia"
        assert mappings[0].source_url == "https://en.wikipedia.org/wiki/Apache_Kafka"
        assert mappings[0].source_title == "Apache Kafka"

    def test_empty_chunks_returns_empty(self):
        assert build_citation_map([]) == []


# ---------------------------------------------------------------------------
# Synthesizer.synthesize tests (Groq API mocked)
# ---------------------------------------------------------------------------

class TestSynthesizerStream:
    @pytest.mark.asyncio
    async def test_empty_chunks_yields_no_sources_message(self, synthesizer: Synthesizer):
        """When no chunks are provided, yield a canned response without calling the LLM."""
        tokens: list[str] = []
        async for token in synthesizer.synthesize("anything", []):
            tokens.append(token)

        full = "".join(tokens)
        assert full == NO_SOURCES_RESPONSE

    @pytest.mark.asyncio
    async def test_streams_tokens_from_groq(
        self,
        synthesizer: Synthesizer,
        sample_chunks: list[RetrievedChunk],
    ):
        """Mocked Groq stream should yield tokens that include citation markers."""
        streamed_tokens = [
            "Kafka ", "uses ", "a ", "distributed ", "commit ", "log ", "[1]. ",
            "RabbitMQ ", "implements ", "AMQP ", "[2].",
        ]

        mock_stream = _make_async_stream(streamed_tokens)
        synthesizer._client.chat.completions.create = AsyncMock(return_value=mock_stream)

        collected: list[str] = []
        async for token in synthesizer.synthesize("Kafka vs RabbitMQ", sample_chunks):
            collected.append(token)

        full_answer = "".join(collected)
        assert "[1]" in full_answer
        assert "[2]" in full_answer
        assert len(collected) == len(streamed_tokens)

    @pytest.mark.asyncio
    async def test_groq_called_with_correct_params(
        self,
        synthesizer: Synthesizer,
        sample_chunks: list[RetrievedChunk],
    ):
        mock_stream = _make_async_stream(["answer"])
        mock_create = AsyncMock(return_value=mock_stream)
        synthesizer._client.chat.completions.create = mock_create

        tokens = []
        async for t in synthesizer.synthesize("test", sample_chunks):
            tokens.append(t)

        mock_create.assert_called_once()
        kwargs = mock_create.call_args.kwargs
        assert kwargs["temperature"] == 0.3
        assert kwargs["max_tokens"] == 2048
        assert kwargs["stream"] is True
        assert kwargs["messages"][0]["role"] == "system"
        assert kwargs["messages"][1]["role"] == "user"

    @pytest.mark.asyncio
    async def test_custom_temperature_and_max_tokens(
        self,
        synthesizer: Synthesizer,
        sample_chunks: list[RetrievedChunk],
    ):
        mock_stream = _make_async_stream(["ok"])
        mock_create = AsyncMock(return_value=mock_stream)
        synthesizer._client.chat.completions.create = mock_create

        async for _ in synthesizer.synthesize(
            "test", sample_chunks, temperature=0.7, max_tokens=512
        ):
            pass

        kwargs = mock_create.call_args.kwargs
        assert kwargs["temperature"] == 0.7
        assert kwargs["max_tokens"] == 512

    @pytest.mark.asyncio
    async def test_skips_empty_delta_content(
        self,
        synthesizer: Synthesizer,
        sample_chunks: list[RetrievedChunk],
    ):
        """Tokens with None or empty content should be silently skipped."""
        mock_stream = _make_async_stream(["hello", None, "", "world"])
        synthesizer._client.chat.completions.create = AsyncMock(return_value=mock_stream)

        collected = []
        async for t in synthesizer.synthesize("test", sample_chunks):
            collected.append(t)

        assert collected == ["hello", "world"]


# ---------------------------------------------------------------------------
# Synthesizer.synthesize_complete tests
# ---------------------------------------------------------------------------

class TestSynthesizeComplete:
    @pytest.mark.asyncio
    async def test_returns_full_answer_and_citations(
        self,
        synthesizer: Synthesizer,
        sample_chunks: list[RetrievedChunk],
    ):
        mock_stream = _make_async_stream(["Answer ", "with ", "[1] ", "citation."])
        synthesizer._client.chat.completions.create = AsyncMock(return_value=mock_stream)

        result = await synthesizer.synthesize_complete("test", sample_chunks)

        assert "Answer" in result.answer
        assert "[1]" in result.answer
        assert len(result.citations) == 3
        assert result.citations[0].citation_id == 1

    @pytest.mark.asyncio
    async def test_empty_chunks_complete(self, synthesizer: Synthesizer):
        result = await synthesizer.synthesize_complete("test", [])

        assert result.answer == NO_SOURCES_RESPONSE
        assert result.citations == []


# ---------------------------------------------------------------------------
# Async stream mock helper
# ---------------------------------------------------------------------------

class _AsyncStreamIter:
    """Mimics the async iterator returned by ``groq`` streaming calls."""

    def __init__(self, tokens: list[str | None]) -> None:
        self._tokens = tokens
        self._idx = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._idx >= len(self._tokens):
            raise StopAsyncIteration
        token = self._tokens[self._idx]
        self._idx += 1
        chunk = MagicMock()
        delta = MagicMock()
        delta.content = token
        chunk.choices = [MagicMock(delta=delta)]
        return chunk


def _make_async_stream(tokens: list[str | None]) -> _AsyncStreamIter:
    return _AsyncStreamIter(tokens)
