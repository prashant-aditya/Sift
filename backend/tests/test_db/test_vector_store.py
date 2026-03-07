"""Tests for VectorStore: upsert, query, metadata filtering, empty collections, persistence."""

from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone

import pytest

from app.db.vector_store import (
    GLOBAL_COLLECTION_NAME,
    CollectionStats,
    RetrievedChunk,
    VectorStore,
)
from app.ingestion.chunker import Chunk

EMBEDDING_DIM = 384


def _random_embedding(seed: float = 0.0) -> list[float]:
    """Deterministic pseudo-random embedding for testing."""
    return [math.sin(seed + i) for i in range(EMBEDDING_DIM)]


def _make_chunk(
    text: str = "sample text",
    source_name: str = "test_source",
    source_url: str = "https://example.com",
    source_title: str = "Test Article",
    chunk_index: int = 0,
    total_chunks: int = 1,
    embedding: list[float] | None = None,
    published_date: datetime | None = None,
) -> Chunk:
    return Chunk(
        chunk_id=str(uuid.uuid4()),
        text=text,
        source_url=source_url,
        source_name=source_name,
        source_title=source_title,
        chunk_index=chunk_index,
        total_chunks=total_chunks,
        published_date=published_date,
        fetched_at=datetime.now(timezone.utc),
        embedding=embedding,
    )


@pytest.fixture()
def store(tmp_path) -> VectorStore:
    """Create a VectorStore backed by a pytest-managed temp directory."""
    return VectorStore(persist_dir=str(tmp_path / "chroma"))


@pytest.fixture()
def persist_dir(tmp_path) -> str:
    """Return a temp path string for persistence tests that need two store instances."""
    return str(tmp_path / "chroma_persist")


# ======================================================================
# Upsert + Query (CP-1.4.5 — core round-trip)
# ======================================================================


class TestUpsertAndQuery:
    def test_upsert_and_query_round_trip(self, store: VectorStore):
        emb = _random_embedding(1.0)
        chunk = _make_chunk(text="Kafka is a distributed event streaming platform.", embedding=emb)

        count = store.upsert_chunks("test_col", [chunk])
        assert count == 1

        results = store.query("test_col", query_embedding=emb, n_results=5)
        assert len(results) == 1
        assert isinstance(results[0], RetrievedChunk)
        assert results[0].chunk.chunk_id == chunk.chunk_id
        assert results[0].chunk.text == chunk.text
        assert results[0].score > 0

    def test_upsert_multiple_chunks_returns_ranked_results(self, store: VectorStore):
        query_emb = _random_embedding(1.0)

        close_chunk = _make_chunk(text="Close match", source_name="close", embedding=_random_embedding(1.0))
        far_chunk = _make_chunk(text="Far match", source_name="far", embedding=_random_embedding(100.0))

        store.upsert_chunks("ranked", [close_chunk, far_chunk])

        results = store.query("ranked", query_embedding=query_emb, n_results=2)
        assert len(results) == 2
        assert results[0].score >= results[1].score
        assert results[0].chunk.chunk_id == close_chunk.chunk_id

    def test_upsert_skips_chunks_without_embeddings(self, store: VectorStore):
        with_emb = _make_chunk(text="Has embedding", embedding=_random_embedding(1.0))
        without_emb = _make_chunk(text="No embedding", embedding=None)

        count = store.upsert_chunks("partial", [with_emb, without_emb])
        assert count == 1

    def test_upsert_all_missing_embeddings_returns_zero(self, store: VectorStore):
        chunk = _make_chunk(text="No embedding", embedding=None)

        count = store.upsert_chunks("empty", [chunk])
        assert count == 0

    def test_upsert_is_idempotent(self, store: VectorStore):
        emb = _random_embedding(2.0)
        chunk = _make_chunk(text="Original text", embedding=emb)

        store.upsert_chunks("idempotent", [chunk])
        store.upsert_chunks("idempotent", [chunk])

        stats = store.get_collection_stats("idempotent")
        assert stats is not None
        assert stats.count == 1

    def test_upsert_updates_existing_chunk(self, store: VectorStore):
        emb = _random_embedding(3.0)
        chunk_id = str(uuid.uuid4())

        original = _make_chunk(text="Version 1", embedding=emb)
        original.chunk_id = chunk_id

        updated = _make_chunk(text="Version 2", embedding=emb)
        updated.chunk_id = chunk_id

        store.upsert_chunks("update_test", [original])
        store.upsert_chunks("update_test", [updated])

        results = store.query("update_test", query_embedding=emb, n_results=5)
        assert len(results) == 1
        assert results[0].chunk.text == "Version 2"


# ======================================================================
# Metadata Filtering (CP-1.4.5 — where clause)
# ======================================================================


class TestMetadataFiltering:
    def test_filter_by_source_name(self, store: VectorStore):
        emb = _random_embedding(5.0)

        wiki_chunk = _make_chunk(text="From Wikipedia", source_name="wikipedia", embedding=_random_embedding(5.0))
        reddit_chunk = _make_chunk(text="From Reddit", source_name="reddit", embedding=_random_embedding(5.1))

        store.upsert_chunks("filter_test", [wiki_chunk, reddit_chunk])

        results = store.query(
            "filter_test",
            query_embedding=emb,
            n_results=10,
            where={"source_name": "wikipedia"},
        )
        assert len(results) == 1
        assert results[0].chunk.source_name == "wikipedia"

    def test_filter_returns_empty_when_no_match(self, store: VectorStore):
        emb = _random_embedding(6.0)
        chunk = _make_chunk(text="Only source", source_name="arxiv", embedding=emb)
        store.upsert_chunks("no_match", [chunk])

        results = store.query(
            "no_match",
            query_embedding=emb,
            where={"source_name": "nonexistent"},
        )
        assert results == []

    def test_metadata_preserves_published_date(self, store: VectorStore):
        emb = _random_embedding(7.0)
        pub_date = datetime(2025, 6, 15, 12, 0, tzinfo=timezone.utc)
        chunk = _make_chunk(text="Dated", embedding=emb, published_date=pub_date)

        store.upsert_chunks("dates", [chunk])
        results = store.query("dates", query_embedding=emb)

        assert len(results) == 1
        assert results[0].chunk.published_date is not None
        assert results[0].chunk.published_date.year == 2025
        assert results[0].chunk.published_date.month == 6

    def test_citation_id_format(self, store: VectorStore):
        emb = _random_embedding(8.0)
        chunk = _make_chunk(text="Citation test", source_name="hackernews", embedding=emb)
        store.upsert_chunks("cite", [chunk])

        results = store.query("cite", query_embedding=emb)
        assert len(results) == 1
        assert results[0].citation_id.startswith("hackernews:")


# ======================================================================
# Empty Collection (CP-1.4.5)
# ======================================================================


class TestEmptyCollection:
    def test_query_empty_collection_returns_empty_list(self, store: VectorStore):
        results = store.query("nonexistent_col", query_embedding=_random_embedding())
        assert results == []

    def test_get_collection_stats_nonexistent(self, store: VectorStore):
        stats = store.get_collection_stats("does_not_exist")
        assert stats is None

    def test_delete_nonexistent_collection_returns_false(self, store: VectorStore):
        assert store.delete_collection("nope") is False


# ======================================================================
# Collection Management
# ======================================================================


class TestCollectionManagement:
    def test_get_or_create_creates_new(self, store: VectorStore):
        col = store.get_or_create_collection("brand_new")
        assert col.count() == 0

    def test_get_collection_stats(self, store: VectorStore):
        emb = _random_embedding(10.0)
        store.upsert_chunks("stats_test", [_make_chunk(embedding=emb)])

        stats = store.get_collection_stats("stats_test")
        assert isinstance(stats, CollectionStats)
        assert stats.name == "stats_test"
        assert stats.count == 1

    def test_delete_collection(self, store: VectorStore):
        store.get_or_create_collection("doomed")
        assert store.delete_collection("doomed") is True
        assert store.get_collection_stats("doomed") is None

    def test_list_collections(self, store: VectorStore):
        store.get_or_create_collection("alpha")
        store.get_or_create_collection("beta")

        names = store.list_collections()
        assert "alpha" in names
        assert "beta" in names


# ======================================================================
# Session & Global Naming Convention (CP-1.4.3 + CP-1.4.5)
# ======================================================================


class TestNamingConvention:
    def test_session_collection_name(self):
        assert VectorStore.collection_name_for_session("abc-123") == "session_abc-123"

    def test_is_session_collection(self):
        assert VectorStore.is_session_collection("session_abc-123") is True
        assert VectorStore.is_session_collection("global") is False

    def test_session_upsert_and_query(self, store: VectorStore):
        sid = "test-session-42"
        emb = _random_embedding(20.0)
        chunk = _make_chunk(text="Session data", embedding=emb)

        store.upsert_session_chunks(sid, [chunk])
        results = store.query_session(sid, query_embedding=emb)

        assert len(results) == 1
        assert results[0].chunk.text == "Session data"

    def test_global_upsert_and_query(self, store: VectorStore):
        emb = _random_embedding(21.0)
        chunk = _make_chunk(text="Global knowledge", embedding=emb)

        store.upsert_global_chunks([chunk])
        results = store.query_global(query_embedding=emb)

        assert len(results) == 1
        assert results[0].chunk.text == "Global knowledge"

    def test_session_and_global_are_isolated(self, store: VectorStore):
        session_emb = _random_embedding(30.0)
        global_emb = _random_embedding(31.0)

        store.upsert_session_chunks("isolated", [_make_chunk(text="Session only", embedding=session_emb)])
        store.upsert_global_chunks([_make_chunk(text="Global only", embedding=global_emb)])

        session_results = store.query_session("isolated", query_embedding=session_emb)
        global_results = store.query_global(query_embedding=global_emb)

        assert len(session_results) == 1
        assert session_results[0].chunk.text == "Session only"
        assert len(global_results) == 1
        assert global_results[0].chunk.text == "Global only"

    def test_delete_session(self, store: VectorStore):
        emb = _random_embedding(32.0)
        store.upsert_session_chunks("del-me", [_make_chunk(embedding=emb)])
        assert store.delete_session("del-me") is True
        assert store.get_collection_stats(VectorStore.collection_name_for_session("del-me")) is None


# ======================================================================
# Persistence Across Restarts (CP-1.4.5)
# ======================================================================


class TestPersistence:
    def test_data_survives_client_recreation(self, persist_dir: str):
        """Simulate a restart by creating a new VectorStore pointing at the same dir."""
        emb = _random_embedding(40.0)
        chunk = _make_chunk(text="Persistent data", embedding=emb)

        store_1 = VectorStore(persist_dir=persist_dir)
        store_1.upsert_chunks("persist_col", [chunk])
        del store_1

        store_2 = VectorStore(persist_dir=persist_dir)
        results = store_2.query("persist_col", query_embedding=emb)

        assert len(results) == 1
        assert results[0].chunk.text == "Persistent data"

    def test_stats_survive_restart(self, persist_dir: str):
        emb = _random_embedding(41.0)
        store_1 = VectorStore(persist_dir=persist_dir)
        store_1.upsert_chunks("persist_stats", [_make_chunk(embedding=emb)])
        del store_1

        store_2 = VectorStore(persist_dir=persist_dir)
        stats = store_2.get_collection_stats("persist_stats")
        assert stats is not None
        assert stats.count == 1

    def test_multiple_collections_persist(self, persist_dir: str):
        emb_a = _random_embedding(42.0)
        emb_b = _random_embedding(43.0)

        store_1 = VectorStore(persist_dir=persist_dir)
        store_1.upsert_session_chunks("sess-a", [_make_chunk(text="A", embedding=emb_a)])
        store_1.upsert_global_chunks([_make_chunk(text="B", embedding=emb_b)])
        del store_1

        store_2 = VectorStore(persist_dir=persist_dir)
        assert store_2.get_collection_stats(VectorStore.collection_name_for_session("sess-a")).count == 1
        assert store_2.get_collection_stats(GLOBAL_COLLECTION_NAME).count == 1
