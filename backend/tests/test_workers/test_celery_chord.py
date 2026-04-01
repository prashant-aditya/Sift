from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from celery import chord

from app.ingestion.chunker import Chunk
from app.sources.base import SourceAdapter, SourceResult
from app.sources.registry import SourceRegistry
from workers.celery_app import celery_app


class FakeAdapter(SourceAdapter):
    name = "fake"
    display_name = "Fake"

    async def search(
        self, query: str, max_results: int | None = None
    ) -> list[SourceResult]:
        out = [
            SourceResult(
                title=f"Result for {query}",
                url=f"https://example.com/{query}",
                snippet="snippet",
                source_name=self.name,
            )
        ]
        return out[: max_results or len(out)]

    def is_available(self) -> bool:
        return True


class FailingAdapter(SourceAdapter):
    name = "failing"
    display_name = "Failing"

    async def search(
        self, query: str, max_results: int | None = None
    ) -> list[SourceResult]:
        raise RuntimeError("boom")

    def is_available(self) -> bool:
        return True


@pytest.fixture(autouse=True)
def eager_mode():
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
    yield


def test_chord_search_and_process_results_eager_mode():
    registry = SourceRegistry()
    registry.register(FakeAdapter())

    async def fake_process(source_results):
        assert len(source_results) >= 1
        return [
            Chunk(
                chunk_id="c1",
                text="chunk text",
                source_url=source_results[0].url,
                source_name=source_results[0].source_name,
                source_title=source_results[0].title,
                chunk_index=0,
                total_chunks=1,
                fetched_at=datetime.now(timezone.utc),
                embedding=[0.1] * 384,
            )
        ]

    fake_pipeline = MagicMock()
    fake_pipeline.process = fake_process

    fake_store = MagicMock()
    fake_store.upsert_chunks = MagicMock(return_value=1)

    with (
        patch("workers.tasks._build_source_registry", return_value=registry),
        patch(
            "workers.callbacks._build_ingestion_pipeline", return_value=fake_pipeline
        ),
        patch("workers.callbacks._build_vector_store", return_value=fake_store),
    ):
        header = [
            celery_app.signature(
                "workers.tasks.search_source",
                kwargs={
                    "source_name": "fake",
                    "sub_queries": ["q1", "q2"],
                    "max_results": 3,
                },
            )
        ]
        callback = celery_app.signature(
            "workers.callbacks.process_results",
            kwargs={"session_id": "session_test"},
        )

        result = chord(header)(callback).get(timeout=5)

    assert result["session_id"] == "session_test"
    assert result["sources_used"] >= 1
    assert isinstance(result["chunks"], list)
    assert result["chunks"][0]["chunk_id"] == "c1"
    assert result["source_counts"]["fake"] >= 1
    assert fake_store.upsert_chunks.called


def test_celery_app_config_has_expected_limits_and_routes():
    assert celery_app.conf.task_soft_time_limit == 15
    assert celery_app.conf.task_time_limit == 20
    assert celery_app.conf.worker_prefetch_multiplier == 1
    assert celery_app.conf.task_acks_late is True

    routes = dict(celery_app.conf.task_routes or {})
    assert routes["workers.tasks.search_source"]["queue"] == "search"
    assert routes["workers.callbacks.process_results"]["queue"] == "ingestion"


def test_search_source_retries_on_exception():
    registry = SourceRegistry()
    registry.register(FailingAdapter())

    with patch("workers.tasks._build_source_registry", return_value=registry):
        # In eager mode, Celery raises Retry immediately when self.retry is called.
        with pytest.raises(Exception) as excinfo:
            celery_app.tasks["workers.tasks.search_source"].apply(
                kwargs={
                    "source_name": "failing",
                    "sub_queries": ["q"],
                    "max_results": 3,
                }
            ).get()

    assert "Retry" in excinfo.exconly() or "boom" in excinfo.exconly()
