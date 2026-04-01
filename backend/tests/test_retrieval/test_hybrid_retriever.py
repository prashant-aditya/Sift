"""Tests for hybrid retrieval (Goal 2.2): dense + BM25 + RRF + diversity."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

import pytest

from app.db.vector_store import RetrievedChunk
from app.ingestion.chunker import Chunk
from app.retrieval.dense import DenseRetriever
from app.retrieval.hybrid_retriever import HybridRetriever, rrf_fuse


def _make_chunk(
    *,
    chunk_id: str,
    text: str,
    source_name: str,
) -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        text=text,
        source_url=f"https://example.com/{chunk_id}",
        source_name=source_name,
        source_title=f"Title {chunk_id}",
        chunk_index=0,
        total_chunks=1,
        fetched_at=datetime.now(timezone.utc),
    )


def _make_retrieved(chunk: Chunk, score: float = 0.9) -> RetrievedChunk:
    return RetrievedChunk(
        chunk=chunk,
        score=score,
        citation_id=f"{chunk.source_name}:{chunk.chunk_id[:8]}",
    )


class _FakeDense(DenseRetriever):
    def __init__(self, ranked: Iterable[RetrievedChunk]) -> None:
        # Don't call parent init (no vector store / embedder needed)
        self._ranked = list(ranked)

    async def retrieve(self, *, query: str, session_id: str, top_k: int = 50, where=None):
        return self._ranked[:top_k]


class TestRRF:
    def test_rrf_boosts_overlap(self) -> None:
        # A appears in both rankings, B only in one.
        fused = rrf_fuse(
            bm25_ranked_ids=["A", "B", "C"],
            dense_ranked_ids=["A", "X", "Y"],
            k=60,
        )
        assert fused["A"] > fused["B"]
        assert fused["A"] > fused["X"]

    def test_rrf_non_overlapping_sets_combines(self) -> None:
        fused = rrf_fuse(
            bm25_ranked_ids=["A", "B"],
            dense_ranked_ids=["X", "Y"],
            k=60,
        )
        assert set(fused.keys()) == {"A", "B", "X", "Y"}


class TestHybridRetriever:
    @pytest.mark.asyncio
    async def test_single_list_degradation_dense_only(self) -> None:
        c1 = _make_chunk(chunk_id="c1", text="alpha beta", source_name="wiki")
        c2 = _make_chunk(chunk_id="c2", text="gamma delta", source_name="wiki")
        dense = _FakeDense([_make_retrieved(c2, 0.9), _make_retrieved(c1, 0.8)])
        retriever = HybridRetriever(dense=dense)

        # Use a query that BM25 cannot match so we degrade to dense-only ranking.
        out = await retriever.retrieve(query="zzzz_unmatched", session_id="s1", chunks=[c1, c2], top_k=2)
        assert [rc.chunk.chunk_id for rc in out] == ["c2", "c1"]

    @pytest.mark.asyncio
    async def test_single_list_degradation_bm25_only(self) -> None:
        c1 = _make_chunk(chunk_id="c1", text="raft consensus protocol", source_name="a")
        c2 = _make_chunk(chunk_id="c2", text="kafka consumer groups", source_name="b")
        dense = _FakeDense([])
        retriever = HybridRetriever(dense=dense)

        out = await retriever.retrieve(query="raft consensus", session_id="s1", chunks=[c1, c2], top_k=2)
        assert out
        assert out[0].chunk.chunk_id == "c1"

    @pytest.mark.asyncio
    async def test_diversity_enforcement_max_3_per_source(self) -> None:
        chunks = [
            _make_chunk(chunk_id=f"a{i}", text=f"alpha {i}", source_name="same")
            for i in range(6)
        ] + [
            _make_chunk(chunk_id="b1", text="alpha other 1", source_name="other"),
            _make_chunk(chunk_id="b2", text="alpha other 2", source_name="other"),
        ]

        # Dense ranks all "same" first to stress diversity enforcement.
        dense_ranked = [_make_retrieved(c, 1.0 - i * 0.01) for i, c in enumerate(chunks)]
        dense = _FakeDense(dense_ranked)
        retriever = HybridRetriever(dense=dense, max_per_source=3)

        out = await retriever.retrieve(query="alpha", session_id="s1", chunks=chunks, top_k=5)
        assert len(out) == 5
        same_count = sum(1 for rc in out if rc.chunk.source_name == "same")
        assert same_count <= 3
        assert sum(1 for rc in out if rc.chunk.source_name == "other") >= 2

