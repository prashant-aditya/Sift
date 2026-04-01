"""Dense retrieval wrapper around the Chroma-backed VectorStore."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Optional

from app.db.vector_store import RetrievedChunk, VectorStore
from app.ingestion.embedder import EmbeddingGenerator


@dataclass
class DenseRetriever:
    """Dense retriever that queries ChromaDB via :class:`VectorStore`."""

    vector_store: VectorStore
    embedder: EmbeddingGenerator

    async def retrieve(
        self,
        *,
        query: str,
        session_id: str,
        top_k: int = 50,
        where: Optional[dict] = None,
    ) -> list[RetrievedChunk]:
        if not query.strip():
            return []

        query_embeddings = await self.embedder.embed([query])
        if not query_embeddings:
            return []

        return await asyncio.to_thread(
            self.vector_store.query_session,
            session_id,
            query_embeddings[0],
            top_k,
            where,
        )
