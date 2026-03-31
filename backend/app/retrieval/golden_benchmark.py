"""Small golden-dataset benchmark for hybrid retrieval (CP-2.2.6).

This is a lightweight, dependency-free benchmark intended for quick sanity checks.
It uses a tiny in-memory corpus of chunks and a 10-query golden set with expected
relevant chunk IDs, then compares BM25-only vs hybrid (BM25 + pseudo-dense + RRF).

Run:
  python3 -m app.retrieval.golden_benchmark
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone

from app.db.vector_store import RetrievedChunk
from app.ingestion.chunker import Chunk
from app.retrieval.bm25 import BM25Index, tokenize
from app.retrieval.hybrid_retriever import HybridRetriever


def _make_chunk(*, chunk_id: str, text: str, source_name: str) -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        text=text,
        source_url=f"https://example.com/{chunk_id}",
        source_name=source_name,
        source_title=f"{source_name}:{chunk_id}",
        chunk_index=0,
        total_chunks=1,
        fetched_at=datetime.now(timezone.utc),
    )


@dataclass
class GoldenExample:
    query: str
    relevant_chunk_ids: set[str]


def _mrr(examples: list[GoldenExample], rankings: dict[str, list[str]]) -> float:
    total = 0.0
    for ex in examples:
        ranked = rankings.get(ex.query, [])
        rr = 0.0
        for rank, cid in enumerate(ranked, start=1):
            if cid in ex.relevant_chunk_ids:
                rr = 1.0 / rank
                break
        total += rr
    return total / max(len(examples), 1)


def _recall_at_k(examples: list[GoldenExample], rankings: dict[str, list[str]], k: int) -> float:
    hits = 0
    for ex in examples:
        topk = set(rankings.get(ex.query, [])[:k])
        if topk & ex.relevant_chunk_ids:
            hits += 1
    return hits / max(len(examples), 1)


class _PseudoDenseRetriever:
    """A deterministic, dependency-free 'dense-ish' retriever using token overlap.

    It intentionally differs from BM25 ranking to exercise RRF fusion without
    requiring embedding models in local dev/CI.
    """

    def __init__(self, chunks: list[Chunk]) -> None:
        self._chunks = chunks
        self._chunk_tokens = {c.chunk_id: set(tokenize(c.text)) for c in chunks}

    async def retrieve(self, *, query: str, session_id: str, top_k: int = 50, where=None):
        q = set(tokenize(query))
        scored: list[tuple[float, Chunk]] = []
        for c in self._chunks:
            overlap = len(q & self._chunk_tokens[c.chunk_id])
            if overlap == 0:
                continue
            # Normalized overlap score to mimic similarity.
            denom = max(len(q) + len(self._chunk_tokens[c.chunk_id]), 1)
            score = (2.0 * overlap) / denom
            scored.append((score, c))

        scored.sort(key=lambda t: t[0], reverse=True)
        out: list[RetrievedChunk] = []
        for score, c in scored[:top_k]:
            out.append(
                RetrievedChunk(
                    chunk=c,
                    score=float(score),
                    citation_id=f"{c.source_name}:{c.chunk_id[:8]}",
                )
            )
        return out


def _build_golden() -> tuple[list[Chunk], list[GoldenExample]]:
    chunks = [
        _make_chunk(chunk_id="c_kafka_1", source_name="wiki", text="Kafka is a distributed event streaming platform with partitions."),
        _make_chunk(chunk_id="c_rabbit_1", source_name="wiki", text="RabbitMQ is a message broker implementing AMQP with queues and exchanges."),
        _make_chunk(chunk_id="c_raft_1", source_name="arxiv", text="Raft is a consensus algorithm that is understandable and leader-based."),
        _make_chunk(chunk_id="c_cqrs_1", source_name="hn", text="CQRS separates reads and writes; event sourcing stores immutable events."),
        _make_chunk(chunk_id="c_cache_1", source_name="reddit", text="Cache invalidation is hard; consider write-through and TTL strategies."),
        _make_chunk(chunk_id="c_k8s_1", source_name="wiki", text="Kubernetes orchestrates containers using pods, deployments, and services."),
        _make_chunk(chunk_id="c_tls_1", source_name="ddg", text="TLS provides encryption in transit; certificates and handshakes establish trust."),
        _make_chunk(chunk_id="c_vectordb_1", source_name="ddg", text="Vector databases store embeddings for similarity search; cosine distance is common."),
        _make_chunk(chunk_id="c_bm25_1", source_name="wiki", text="BM25 is a bag-of-words ranking function using term frequency and inverse document frequency."),
        _make_chunk(chunk_id="c_rrf_1", source_name="arxiv", text="Reciprocal Rank Fusion combines rankings via 1/(k + rank) without score normalization."),
    ]

    golden = [
        GoldenExample(query="what is kafka used for", relevant_chunk_ids={"c_kafka_1"}),
        GoldenExample(query="rabbitmq amqp queues exchanges", relevant_chunk_ids={"c_rabbit_1"}),
        GoldenExample(query="raft leader based consensus", relevant_chunk_ids={"c_raft_1"}),
        GoldenExample(query="cqrs versus event sourcing", relevant_chunk_ids={"c_cqrs_1"}),
        GoldenExample(query="cache invalidation strategies ttl", relevant_chunk_ids={"c_cache_1"}),
        GoldenExample(query="kubernetes pods deployments services", relevant_chunk_ids={"c_k8s_1"}),
        GoldenExample(query="tls handshake certificates", relevant_chunk_ids={"c_tls_1"}),
        GoldenExample(query="vector database cosine similarity", relevant_chunk_ids={"c_vectordb_1"}),
        GoldenExample(query="bm25 idf term frequency", relevant_chunk_ids={"c_bm25_1"}),
        GoldenExample(query="reciprocal rank fusion rrf formula", relevant_chunk_ids={"c_rrf_1"}),
    ]

    return chunks, golden


async def _run() -> None:
    chunks, golden = _build_golden()

    # BM25-only baseline.
    bm25 = BM25Index().fit([c.text for c in chunks])
    bm25_rankings: dict[str, list[str]] = {}
    for ex in golden:
        res = bm25.query(ex.query, top_k=10)
        bm25_rankings[ex.query] = [chunks[r.doc_index].chunk_id for r in res]

    # Hybrid with pseudo-dense + RRF.
    pseudo_dense = _PseudoDenseRetriever(chunks)
    hybrid = HybridRetriever(dense=pseudo_dense, bm25_top_k=10, dense_top_k=10)
    hybrid_rankings: dict[str, list[str]] = {}
    for ex in golden:
        out = await hybrid.retrieve(query=ex.query, session_id="golden", chunks=chunks, top_k=10)
        hybrid_rankings[ex.query] = [rc.chunk.chunk_id for rc in out]

    print("Golden benchmark (10 queries)")
    print(f"BM25  MRR:     {_mrr(golden, bm25_rankings):.3f}")
    print(f"Hybrid MRR:    {_mrr(golden, hybrid_rankings):.3f}")
    print(f"BM25  R@1:     {_recall_at_k(golden, bm25_rankings, 1):.3f}")
    print(f"Hybrid R@1:    {_recall_at_k(golden, hybrid_rankings, 1):.3f}")
    print(f"BM25  R@5:     {_recall_at_k(golden, bm25_rankings, 5):.3f}")
    print(f"Hybrid R@5:    {_recall_at_k(golden, hybrid_rankings, 5):.3f}")


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()

