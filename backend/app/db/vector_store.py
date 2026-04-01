"""ChromaDB vector store wrapper for semantic chunk storage and retrieval."""

from __future__ import annotations

import logging
from typing import Any, Optional

import chromadb
import chromadb.errors
from pydantic import BaseModel

from app.config import get_settings
from app.ingestion.chunker import Chunk

logger = logging.getLogger(__name__)

SESSION_COLLECTION_PREFIX = "session_"
GLOBAL_COLLECTION_NAME = "global"


class RetrievedChunk(BaseModel):
    """A chunk returned from a vector similarity query."""

    chunk: Chunk
    score: float
    citation_id: str


class CollectionStats(BaseModel):
    """Summary statistics for a ChromaDB collection."""

    name: str
    count: int


class VectorStore:
    """Thin wrapper around :class:`chromadb.PersistentClient`.

    Manages session-scoped and global collections with a consistent naming
    convention and exposes high-level operations for upserting, querying,
    and managing chunked document embeddings.

    Parameters
    ----------
    persist_dir:
        Directory where ChromaDB persists data.  When *None*, the value is
        read from ``Settings.chroma_persist_dir``.
    """

    def __init__(self, persist_dir: Optional[str] = None) -> None:
        self._persist_dir = persist_dir or get_settings().chroma_persist_dir
        self._client = chromadb.PersistentClient(path=self._persist_dir)

    # ------------------------------------------------------------------
    # Collection helpers
    # ------------------------------------------------------------------

    @staticmethod
    def collection_name_for_session(session_id: str) -> str:
        """Return the canonical collection name for a research session."""
        return f"{SESSION_COLLECTION_PREFIX}{session_id}"

    @staticmethod
    def is_session_collection(name: str) -> bool:
        return name.startswith(SESSION_COLLECTION_PREFIX)

    def get_or_create_collection(
        self,
        name: str,
        *,
        metadata: Optional[dict[str, Any]] = None,
    ) -> chromadb.Collection:
        """Return an existing collection or create a new one.

        The collection uses cosine distance by default, which is the standard
        metric for normalised sentence-transformer embeddings.
        """
        collection_metadata = {"hnsw:space": "cosine"}
        if metadata:
            collection_metadata.update(metadata)

        collection = self._client.get_or_create_collection(
            name=name,
            metadata=collection_metadata,
        )
        logger.debug(
            "get_or_create_collection name=%s count=%d", name, collection.count()
        )
        return collection

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def upsert_chunks(
        self,
        collection_name: str,
        chunks: list[Chunk],
    ) -> int:
        """Upsert a batch of :class:`Chunk` objects into *collection_name*.

        Each chunk **must** carry a pre-computed ``embedding``.  Chunks
        without embeddings are silently skipped.

        Returns the number of chunks actually upserted.
        """
        valid = [c for c in chunks if c.embedding is not None]
        if not valid:
            logger.warning("upsert_chunks called with 0 valid embeddings; skipping")
            return 0

        collection = self.get_or_create_collection(collection_name)

        ids = [c.chunk_id for c in valid]
        embeddings = [c.embedding for c in valid]  # type: ignore[misc]
        documents = [c.text for c in valid]
        metadatas = [_chunk_metadata(c) for c in valid]

        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )
        logger.info(
            "Upserted %d chunks into collection '%s'",
            len(valid),
            collection_name,
        )
        return len(valid)

    # ------------------------------------------------------------------
    # Read / query operations
    # ------------------------------------------------------------------

    def query(
        self,
        collection_name: str,
        query_embedding: list[float],
        n_results: int = 10,
        where: Optional[dict[str, Any]] = None,
    ) -> list[RetrievedChunk]:
        """Run a nearest-neighbour search against *collection_name*.

        Parameters
        ----------
        query_embedding:
            The dense vector for the user query.
        n_results:
            Maximum number of results to return.
        where:
            Optional ChromaDB ``where`` filter for metadata
            (e.g. ``{"source_name": "wikipedia"}``).

        Returns
        -------
        list[RetrievedChunk]
            Results sorted by ascending distance (best match first).
        """
        collection = self.get_or_create_collection(collection_name)

        if collection.count() == 0:
            return []

        n_results = min(n_results, collection.count())

        query_kwargs: dict[str, Any] = {
            "query_embeddings": [query_embedding],
            "n_results": n_results,
            "include": ["documents", "metadatas", "distances", "embeddings"],
        }
        if where:
            query_kwargs["where"] = where

        results = collection.query(**query_kwargs)

        return _parse_query_results(results)

    # ------------------------------------------------------------------
    # Collection management
    # ------------------------------------------------------------------

    def delete_collection(self, name: str) -> bool:
        """Delete a collection by name.  Returns *True* if it existed."""
        try:
            self._client.delete_collection(name=name)
            logger.info("Deleted collection '%s'", name)
            return True
        except (ValueError, chromadb.errors.NotFoundError):
            logger.debug("Collection '%s' does not exist; nothing to delete", name)
            return False

    def get_collection_stats(self, name: str) -> Optional[CollectionStats]:
        """Return stats for a collection, or *None* if it does not exist."""
        try:
            collection = self._client.get_collection(name=name)
        except (ValueError, chromadb.errors.NotFoundError):
            return None
        return CollectionStats(name=name, count=collection.count())

    def list_collections(self) -> list[str]:
        """Return the names of all existing collections."""
        return [c.name for c in self._client.list_collections()]

    # ------------------------------------------------------------------
    # Convenience: session & global shortcuts
    # ------------------------------------------------------------------

    def upsert_session_chunks(self, session_id: str, chunks: list[Chunk]) -> int:
        return self.upsert_chunks(self.collection_name_for_session(session_id), chunks)

    def query_session(
        self,
        session_id: str,
        query_embedding: list[float],
        n_results: int = 10,
        where: Optional[dict[str, Any]] = None,
    ) -> list[RetrievedChunk]:
        return self.query(
            self.collection_name_for_session(session_id),
            query_embedding,
            n_results=n_results,
            where=where,
        )

    def upsert_global_chunks(self, chunks: list[Chunk]) -> int:
        return self.upsert_chunks(GLOBAL_COLLECTION_NAME, chunks)

    def query_global(
        self,
        query_embedding: list[float],
        n_results: int = 10,
        where: Optional[dict[str, Any]] = None,
    ) -> list[RetrievedChunk]:
        return self.query(
            GLOBAL_COLLECTION_NAME,
            query_embedding,
            n_results=n_results,
            where=where,
        )

    def delete_session(self, session_id: str) -> bool:
        return self.delete_collection(self.collection_name_for_session(session_id))


# ------------------------------------------------------------------
# Private helpers
# ------------------------------------------------------------------


def _chunk_metadata(chunk: Chunk) -> dict[str, Any]:
    """Build the flat metadata dict stored alongside each vector."""
    meta: dict[str, Any] = {
        "source_url": chunk.source_url,
        "source_name": chunk.source_name,
        "source_title": chunk.source_title,
        "chunk_index": chunk.chunk_index,
        "total_chunks": chunk.total_chunks,
        "fetched_at": chunk.fetched_at.isoformat(),
    }
    if chunk.published_date is not None:
        meta["published_date"] = chunk.published_date.isoformat()
    return meta


def _parse_query_results(results: dict[str, Any]) -> list[RetrievedChunk]:
    """Convert raw ChromaDB query results into :class:`RetrievedChunk` list."""
    retrieved: list[RetrievedChunk] = []

    ids = results.get("ids", [[]])[0]
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]
    raw_embeddings = results.get("embeddings")
    embeddings_list: list = raw_embeddings[0] if raw_embeddings is not None else []

    from datetime import datetime, timezone

    for idx, chunk_id in enumerate(ids):
        meta = metadatas[idx] if idx < len(metadatas) else {}
        doc = documents[idx] if idx < len(documents) else ""
        dist = distances[idx] if idx < len(distances) else 1.0
        emb = embeddings_list[idx] if idx < len(embeddings_list) else None

        published_date = None
        if meta.get("published_date"):
            try:
                published_date = datetime.fromisoformat(meta["published_date"])
            except (ValueError, TypeError):
                pass

        fetched_at_str = meta.get("fetched_at", "")
        try:
            fetched_at = datetime.fromisoformat(fetched_at_str)
        except (ValueError, TypeError):
            fetched_at = datetime.now(timezone.utc)

        chunk = Chunk(
            chunk_id=chunk_id,
            text=doc,
            source_url=meta.get("source_url", ""),
            source_name=meta.get("source_name", ""),
            source_title=meta.get("source_title", ""),
            chunk_index=meta.get("chunk_index", 0),
            total_chunks=meta.get("total_chunks", 1),
            published_date=published_date,
            fetched_at=fetched_at,
            embedding=emb,
        )

        score = 1.0 - dist

        citation_id = f"{meta.get('source_name', 'unknown')}:{chunk_id[:8]}"

        retrieved.append(
            RetrievedChunk(chunk=chunk, score=score, citation_id=citation_id)
        )

    return retrieved
