"""Hybrid retrieval: BM25 (sparse) + dense (Chroma) with Reciprocal Rank Fusion."""

from __future__ import annotations

from dataclasses import dataclass

from app.db.vector_store import RetrievedChunk
from app.ingestion.chunker import Chunk
from app.retrieval.bm25 import BM25Index
from app.retrieval.dense import DenseRetriever


def _citation_id_for_chunk(chunk: Chunk) -> str:
    source_name = chunk.source_name or "unknown"
    return f"{source_name}:{chunk.chunk_id[:8]}"


def _enforce_source_diversity(
    ranked: list[RetrievedChunk],
    *,
    top_k: int,
    max_per_source: int,
) -> list[RetrievedChunk]:
    if max_per_source <= 0:
        return ranked[:top_k]

    counts: dict[str, int] = {}
    out: list[RetrievedChunk] = []
    for rc in ranked:
        src = rc.chunk.source_name or "unknown"
        if counts.get(src, 0) >= max_per_source:
            continue
        counts[src] = counts.get(src, 0) + 1
        out.append(rc)
        if len(out) >= top_k:
            break
    return out


def rrf_fuse(
    *,
    bm25_ranked_ids: list[str],
    dense_ranked_ids: list[str],
    k: int = 60,
) -> dict[str, float]:
    """Return doc_id -> RRF score using 1/(k + rank) with 1-indexed ranks."""
    scores: dict[str, float] = {}
    for rank, doc_id in enumerate(bm25_ranked_ids, start=1):
        scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
    for rank, doc_id in enumerate(dense_ranked_ids, start=1):
        scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
    return scores


@dataclass
class HybridRetriever:
    """Hybrid retriever with RRF fusion and source diversity enforcement."""

    dense: DenseRetriever
    rrf_k: int = 60
    bm25_top_k: int = 50
    dense_top_k: int = 50
    max_per_source: int = 3

    async def retrieve(
        self,
        *,
        query: str,
        session_id: str,
        chunks: list[Chunk],
        top_k: int = 15,
    ) -> list[RetrievedChunk]:
        if not query.strip():
            return []
        if not chunks:
            return []

        # Sparse (BM25) ranking over the session's chunks (in-memory).
        corpus = [c.text for c in chunks]
        bm25 = BM25Index().fit(corpus)
        bm25_results = bm25.query(query, top_k=min(self.bm25_top_k, len(corpus)))
        bm25_ranked_ids = [chunks[r.doc_index].chunk_id for r in bm25_results]

        # Dense ranking via Chroma.
        dense_results = await self.dense.retrieve(
            query=query,
            session_id=session_id,
            top_k=self.dense_top_k,
        )
        dense_ranked_ids = [rc.chunk.chunk_id for rc in dense_results]

        by_id: dict[str, Chunk] = {c.chunk_id: c for c in chunks}

        # Graceful degradation to a single list when the other is empty.
        if not dense_ranked_ids and bm25_ranked_ids:
            ranked = [
                RetrievedChunk(
                    chunk=by_id[cid],
                    score=float(bm25_results[idx].score),
                    citation_id=_citation_id_for_chunk(by_id[cid]),
                )
                for idx, cid in enumerate(bm25_ranked_ids)
                if cid in by_id
            ]
            return _enforce_source_diversity(
                ranked, top_k=top_k, max_per_source=self.max_per_source
            )

        if not bm25_ranked_ids and dense_results:
            return _enforce_source_diversity(
                dense_results, top_k=top_k, max_per_source=self.max_per_source
            )

        fused = rrf_fuse(
            bm25_ranked_ids=bm25_ranked_ids,
            dense_ranked_ids=dense_ranked_ids,
            k=self.rrf_k,
        )

        fused_ranked_ids = sorted(fused.keys(), key=lambda d: fused[d], reverse=True)

        # Construct RetrievedChunk objects from the original chunk metadata.
        fused_ranked: list[RetrievedChunk] = []
        for cid in fused_ranked_ids:
            chunk = by_id.get(cid)
            if chunk is None:
                continue
            fused_ranked.append(
                RetrievedChunk(
                    chunk=chunk,
                    score=float(fused[cid]),
                    citation_id=_citation_id_for_chunk(chunk),
                )
            )

        return _enforce_source_diversity(
            fused_ranked, top_k=top_k, max_per_source=self.max_per_source
        )

