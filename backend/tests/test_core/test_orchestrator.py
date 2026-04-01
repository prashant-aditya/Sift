"""Tests for app.core.orchestrator — research pipeline orchestration.

Covers:
  - Full pipeline e2e with mocked sources and mocked LLM
  - Partial source failure (1 of 3 fails → still returns results)
  - Empty results handling
  - SSE event format validation
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from app.core.orchestrator import (
    DEPTH_CONFIG,
    ResearchOrchestrator,
    _aggregate_source_counts,
    _sse_event,
)
from app.db.vector_store import RetrievedChunk
from app.ingestion.chunker import Chunk
from app.sources.base import SourceAdapter, SourceResult
from app.sources.registry import SourceRegistry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_source_result(
    *,
    title: str = "Test Article",
    url: str = "https://example.com/article",
    snippet: str = "A test snippet.",
    source_name: str = "duckduckgo",
) -> SourceResult:
    return SourceResult(
        title=title,
        url=url,
        snippet=snippet,
        source_name=source_name,
    )


def _make_chunk(
    *,
    text: str = "Sample chunk text",
    chunk_id: str = "chunk-001",
    source_name: str = "duckduckgo",
    source_url: str = "https://example.com",
    source_title: str = "Test",
    embedding: list[float] | None = None,
) -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        text=text,
        source_url=source_url,
        source_name=source_name,
        source_title=source_title,
        chunk_index=0,
        total_chunks=1,
        fetched_at=datetime.now(timezone.utc),
        embedding=embedding or [0.1] * 384,
    )


def _make_retrieved_chunk(
    *,
    text: str = "Retrieved text",
    chunk_id: str = "chunk-001",
    source_name: str = "duckduckgo",
    source_url: str = "https://example.com",
    source_title: str = "Test Article",
    score: float = 0.92,
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


class FakeAdapter(SourceAdapter):
    """A controllable fake source adapter for testing."""

    def __init__(
        self,
        name: str = "fake",
        display_name: str = "Fake Source",
        results: list[SourceResult] | None = None,
        error: Exception | None = None,
        available: bool = True,
    ) -> None:
        self.name = name
        self.display_name = display_name
        self._results = results or []
        self._error = error
        self._available = available

    async def search(self, query: str, max_results: int | None = None) -> list[SourceResult]:
        if self._error:
            raise self._error
        return self._results[: max_results or len(self._results)]

    def is_available(self) -> bool:
        return self._available


async def _collect_events(gen) -> list[dict]:
    """Drain an async generator and parse SSE event data."""
    events: list[dict] = []
    async for raw_event in gen:
        parsed = {
            "event": raw_event["event"],
            "data": json.loads(raw_event["data"]),
        }
        events.append(parsed)
    return events


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_query_analyzer():
    analyzer = MagicMock()
    analyzer.decompose = AsyncMock(return_value=["sub-query-1", "sub-query-2"])
    return analyzer


@pytest.fixture()
def mock_ingestion_pipeline():
    pipeline = MagicMock()
    chunks = [
        _make_chunk(chunk_id="c1", text="chunk 1 text", source_name="duckduckgo"),
        _make_chunk(chunk_id="c2", text="chunk 2 text", source_name="wikipedia"),
    ]
    pipeline.process = AsyncMock(return_value=chunks)
    return pipeline


@pytest.fixture()
def mock_vector_store():
    store = MagicMock()
    store.upsert_chunks = MagicMock(return_value=2)

    retrieved = [
        _make_retrieved_chunk(chunk_id="c1", text="relevant chunk 1", source_name="duckduckgo"),
        _make_retrieved_chunk(chunk_id="c2", text="relevant chunk 2", source_name="wikipedia"),
    ]
    store.query_session = MagicMock(return_value=retrieved)
    return store


@pytest.fixture()
def mock_embedder():
    # Still used by DenseRetriever under the hood, but orchestrator no longer
    # calls embedder directly.
    embedder = MagicMock()
    embedder.embed = AsyncMock(return_value=[[0.1] * 384])
    return embedder


@pytest.fixture()
def mock_synthesizer():
    synth = MagicMock()

    async def fake_synthesize(query, chunks, **kwargs):
        for token in ["Hello ", "world ", "[1]."]:
            yield token

    synth.synthesize = fake_synthesize
    return synth


@pytest.fixture()
def source_registry_with_adapters():
    registry = SourceRegistry()
    registry.register(FakeAdapter(
        name="duckduckgo",
        display_name="DuckDuckGo",
        results=[
            _make_source_result(source_name="duckduckgo", title="DDG Result 1"),
            _make_source_result(source_name="duckduckgo", title="DDG Result 2"),
        ],
    ))
    registry.register(FakeAdapter(
        name="wikipedia",
        display_name="Wikipedia",
        results=[
            _make_source_result(source_name="wikipedia", title="Wiki Result"),
        ],
    ))
    return registry


@pytest.fixture()
def orchestrator(
    mock_query_analyzer,
    source_registry_with_adapters,
    mock_ingestion_pipeline,
    mock_vector_store,
    mock_embedder,
    mock_synthesizer,
):
    return ResearchOrchestrator(
        query_analyzer=mock_query_analyzer,
        source_registry=source_registry_with_adapters,
        ingestion_pipeline=mock_ingestion_pipeline,
        vector_store=mock_vector_store,
        embedder=mock_embedder,
        synthesizer=mock_synthesizer,
    )


# ---------------------------------------------------------------------------
# _sse_event unit tests
# ---------------------------------------------------------------------------

class TestSSEEvent:
    def test_returns_dict_with_event_and_json_data(self):
        result = _sse_event("status", {"phase": "decomposing"})

        assert result["event"] == "status"
        parsed = json.loads(result["data"])
        assert parsed["phase"] == "decomposing"

    def test_handles_nested_data(self):
        result = _sse_event("complete", {
            "session_id": "s1",
            "citations": [{"id": 1, "url": "https://example.com"}],
        })
        parsed = json.loads(result["data"])
        assert parsed["citations"][0]["id"] == 1


# ---------------------------------------------------------------------------
# _aggregate_source_counts unit tests
# ---------------------------------------------------------------------------

class TestAggregateSourceCounts:
    def test_counts_by_source_name(self):
        results = [
            _make_source_result(source_name="duckduckgo"),
            _make_source_result(source_name="duckduckgo"),
            _make_source_result(source_name="wikipedia"),
        ]
        counts = _aggregate_source_counts(results)
        counts_dict = dict(counts)

        assert counts_dict["duckduckgo"] == 2
        assert counts_dict["wikipedia"] == 1

    def test_empty_results(self):
        assert _aggregate_source_counts([]) == []


# ---------------------------------------------------------------------------
# Full pipeline e2e (all mocked)
# ---------------------------------------------------------------------------

class TestResearchPipelineE2E:
    @pytest.mark.asyncio
    async def test_full_pipeline_yields_expected_event_sequence(self, orchestrator):
        """The pipeline should yield events in order: status phases → source_complete → tokens → complete."""
        events = await _collect_events(orchestrator.research("test query"))

        event_types = [e["event"] for e in events]

        assert event_types[0] == "status"
        assert events[0]["data"]["phase"] == "decomposing"

        assert "status" in event_types
        assert "source_complete" in event_types
        assert "token" in event_types
        assert event_types[-1] == "complete"

    @pytest.mark.asyncio
    async def test_complete_event_has_session_id_and_citations(self, orchestrator):
        events = await _collect_events(orchestrator.research("test query"))

        complete = next(e for e in events if e["event"] == "complete")

        assert "session_id" in complete["data"]
        UUID(str(complete["data"]["session_id"]))
        assert isinstance(complete["data"]["citations"], list)
        assert len(complete["data"]["citations"]) > 0
        assert complete["data"]["sources_used"] > 0

    @pytest.mark.asyncio
    async def test_token_events_contain_content(self, orchestrator):
        events = await _collect_events(orchestrator.research("test query"))

        tokens = [e for e in events if e["event"] == "token"]

        assert len(tokens) == 3
        full_text = "".join(t["data"]["content"] for t in tokens)
        assert "Hello world [1]." == full_text

    @pytest.mark.asyncio
    async def test_decomposed_phase_contains_sub_queries(self, orchestrator):
        events = await _collect_events(orchestrator.research("test query"))

        decomposed = next(
            e for e in events
            if e["event"] == "status" and e["data"].get("phase") == "decomposed"
        )
        assert decomposed["data"]["sub_queries"] == ["sub-query-1", "sub-query-2"]

    @pytest.mark.asyncio
    async def test_searching_phase_shows_active_sources(self, orchestrator):
        events = await _collect_events(orchestrator.research("test query"))

        searching = next(
            e for e in events
            if e["event"] == "status" and e["data"].get("phase") == "searching"
        )
        assert searching["data"]["sources_active"] == 2
        assert searching["data"]["sub_queries_count"] == 2

    @pytest.mark.asyncio
    async def test_source_complete_events_emitted(self, orchestrator):
        events = await _collect_events(orchestrator.research("test query"))

        source_completes = [e for e in events if e["event"] == "source_complete"]

        assert len(source_completes) >= 1
        source_names = {e["data"]["source"] for e in source_completes}
        assert "duckduckgo" in source_names or "wikipedia" in source_names

    @pytest.mark.asyncio
    async def test_all_pipeline_phases_present(self, orchestrator):
        events = await _collect_events(orchestrator.research("test query"))

        status_phases = [
            e["data"]["phase"]
            for e in events if e["event"] == "status"
        ]
        for expected in ["decomposing", "decomposed", "searching", "processing", "storing", "retrieving", "synthesizing"]:
            assert expected in status_phases, f"Missing phase: {expected}"

    @pytest.mark.asyncio
    async def test_depth_quick_uses_correct_config(
        self, mock_query_analyzer, mock_ingestion_pipeline,
        mock_vector_store, mock_embedder, mock_synthesizer,
    ):
        registry = SourceRegistry()
        adapter = FakeAdapter(
            name="test",
            display_name="Test",
            results=[_make_source_result(source_name="test")],
        )
        registry.register(adapter)

        orch = ResearchOrchestrator(
            query_analyzer=mock_query_analyzer,
            source_registry=registry,
            ingestion_pipeline=mock_ingestion_pipeline,
            vector_store=mock_vector_store,
            embedder=mock_embedder,
            synthesizer=mock_synthesizer,
        )

        events = await _collect_events(orch.research("test", depth="quick"))

        assert mock_vector_store.query_session.called
        # DenseRetriever fetches dense_top_k (=50) for hybrid fusion.
        call_args = mock_vector_store.query_session.call_args
        assert call_args[0][2] == 50

    @pytest.mark.asyncio
    async def test_depth_deep_uses_correct_config(
        self, mock_query_analyzer, mock_ingestion_pipeline,
        mock_vector_store, mock_embedder, mock_synthesizer,
    ):
        registry = SourceRegistry()
        adapter = FakeAdapter(
            name="test",
            display_name="Test",
            results=[_make_source_result(source_name="test")],
        )
        registry.register(adapter)

        orch = ResearchOrchestrator(
            query_analyzer=mock_query_analyzer,
            source_registry=registry,
            ingestion_pipeline=mock_ingestion_pipeline,
            vector_store=mock_vector_store,
            embedder=mock_embedder,
            synthesizer=mock_synthesizer,
        )

        events = await _collect_events(orch.research("test", depth="deep"))

        call_args = mock_vector_store.query_session.call_args
        assert call_args[0][2] == 50

    @pytest.mark.asyncio
    async def test_specific_sources_filter(
        self, mock_query_analyzer, mock_ingestion_pipeline,
        mock_vector_store, mock_embedder, mock_synthesizer,
        source_registry_with_adapters,
    ):
        """When sources=['wikipedia'], only that adapter should be searched."""
        orch = ResearchOrchestrator(
            query_analyzer=mock_query_analyzer,
            source_registry=source_registry_with_adapters,
            ingestion_pipeline=mock_ingestion_pipeline,
            vector_store=mock_vector_store,
            embedder=mock_embedder,
            synthesizer=mock_synthesizer,
        )

        events = await _collect_events(orch.research("test", sources=["wikipedia"]))

        source_completes = [e for e in events if e["event"] == "source_complete"]
        source_names = {e["data"]["source"] for e in source_completes}
        assert "wikipedia" in source_names


# ---------------------------------------------------------------------------
# Partial source failure
# ---------------------------------------------------------------------------

class TestPartialSourceFailure:
    @pytest.mark.asyncio
    async def test_one_of_three_fails_still_returns_results(
        self, mock_query_analyzer, mock_ingestion_pipeline,
        mock_vector_store, mock_embedder, mock_synthesizer,
    ):
        """If one source raises, the pipeline continues with the others."""
        registry = SourceRegistry()
        registry.register(FakeAdapter(
            name="good1",
            display_name="Good 1",
            results=[_make_source_result(source_name="good1")],
        ))
        registry.register(FakeAdapter(
            name="failing",
            display_name="Failing",
            error=RuntimeError("connection timeout"),
        ))
        registry.register(FakeAdapter(
            name="good2",
            display_name="Good 2",
            results=[_make_source_result(source_name="good2")],
        ))

        orch = ResearchOrchestrator(
            query_analyzer=mock_query_analyzer,
            source_registry=registry,
            ingestion_pipeline=mock_ingestion_pipeline,
            vector_store=mock_vector_store,
            embedder=mock_embedder,
            synthesizer=mock_synthesizer,
        )

        events = await _collect_events(orch.research("test"))

        event_types = [e["event"] for e in events]
        assert "complete" in event_types

        complete = next(e for e in events if e["event"] == "complete")
        assert complete["data"]["sources_used"] > 0
        assert complete["data"]["citations"] is not None

    @pytest.mark.asyncio
    async def test_partial_failure_records_errors(
        self, mock_query_analyzer, mock_ingestion_pipeline,
        mock_vector_store, mock_embedder, mock_synthesizer,
    ):
        """Errors from failing sources should be included in the complete event."""
        registry = SourceRegistry()
        registry.register(FakeAdapter(
            name="good",
            display_name="Good",
            results=[_make_source_result(source_name="good")],
        ))
        registry.register(FakeAdapter(
            name="bad",
            display_name="Bad",
            error=ValueError("API key invalid"),
        ))

        orch = ResearchOrchestrator(
            query_analyzer=mock_query_analyzer,
            source_registry=registry,
            ingestion_pipeline=mock_ingestion_pipeline,
            vector_store=mock_vector_store,
            embedder=mock_embedder,
            synthesizer=mock_synthesizer,
        )

        events = await _collect_events(orch.research("test"))
        complete = next(e for e in events if e["event"] == "complete")

        assert "errors" in complete["data"]
        errors = complete["data"]["errors"]
        assert any("bad" in err and "API key invalid" in err for err in errors)

    @pytest.mark.asyncio
    async def test_all_sources_fail_yields_empty_complete(
        self, mock_query_analyzer, mock_ingestion_pipeline,
        mock_vector_store, mock_embedder, mock_synthesizer,
    ):
        """When every source fails, the pipeline completes gracefully with empty results."""
        registry = SourceRegistry()
        registry.register(FakeAdapter(
            name="fail1",
            display_name="Fail 1",
            error=RuntimeError("down"),
        ))
        registry.register(FakeAdapter(
            name="fail2",
            display_name="Fail 2",
            error=TimeoutError("timeout"),
        ))

        orch = ResearchOrchestrator(
            query_analyzer=mock_query_analyzer,
            source_registry=registry,
            ingestion_pipeline=mock_ingestion_pipeline,
            vector_store=mock_vector_store,
            embedder=mock_embedder,
            synthesizer=mock_synthesizer,
        )

        events = await _collect_events(orch.research("test"))

        complete = next(e for e in events if e["event"] == "complete")
        assert complete["data"]["sources_used"] == 0
        assert complete["data"]["citations"] == []
        assert complete["data"]["errors"] is not None


# ---------------------------------------------------------------------------
# Empty results handling
# ---------------------------------------------------------------------------

class TestEmptyResults:
    @pytest.mark.asyncio
    async def test_sources_return_empty_lists(
        self, mock_query_analyzer, mock_ingestion_pipeline,
        mock_vector_store, mock_embedder, mock_synthesizer,
    ):
        """All sources succeed but return zero results."""
        registry = SourceRegistry()
        registry.register(FakeAdapter(
            name="empty",
            display_name="Empty",
            results=[],
        ))

        orch = ResearchOrchestrator(
            query_analyzer=mock_query_analyzer,
            source_registry=registry,
            ingestion_pipeline=mock_ingestion_pipeline,
            vector_store=mock_vector_store,
            embedder=mock_embedder,
            synthesizer=mock_synthesizer,
        )

        events = await _collect_events(orch.research("obscure query"))

        complete = next(e for e in events if e["event"] == "complete")
        assert complete["data"]["sources_used"] == 0
        assert complete["data"]["citations"] == []

    @pytest.mark.asyncio
    async def test_ingestion_produces_no_chunks(
        self, mock_query_analyzer, source_registry_with_adapters,
        mock_vector_store, mock_embedder, mock_synthesizer,
    ):
        """Sources return results, but ingestion produces no viable chunks."""
        empty_pipeline = MagicMock()
        empty_pipeline.process = AsyncMock(return_value=[])

        orch = ResearchOrchestrator(
            query_analyzer=mock_query_analyzer,
            source_registry=source_registry_with_adapters,
            ingestion_pipeline=empty_pipeline,
            vector_store=mock_vector_store,
            embedder=mock_embedder,
            synthesizer=mock_synthesizer,
        )

        events = await _collect_events(orch.research("test"))

        complete = next(e for e in events if e["event"] == "complete")
        assert complete["data"]["citations"] == []
        assert mock_vector_store.upsert_chunks.call_count == 0

    @pytest.mark.asyncio
    async def test_no_available_adapters(
        self, mock_query_analyzer, mock_ingestion_pipeline,
        mock_vector_store, mock_embedder, mock_synthesizer,
    ):
        """Empty registry should yield immediate complete with error."""
        empty_registry = SourceRegistry()

        orch = ResearchOrchestrator(
            query_analyzer=mock_query_analyzer,
            source_registry=empty_registry,
            ingestion_pipeline=mock_ingestion_pipeline,
            vector_store=mock_vector_store,
            embedder=mock_embedder,
            synthesizer=mock_synthesizer,
        )

        events = await _collect_events(orch.research("test"))

        complete = next(e for e in events if e["event"] == "complete")
        assert complete["data"]["sources_used"] == 0
        assert "No available sources" in complete["data"]["errors"]


# ---------------------------------------------------------------------------
# SSE event format validation
# ---------------------------------------------------------------------------

class TestSSEEventFormat:
    @pytest.mark.asyncio
    async def test_all_events_have_event_and_data_keys(self, orchestrator):
        """Every yielded dict must have 'event' (str) and 'data' (valid JSON str)."""
        async for raw_event in orchestrator.research("test query"):
            assert "event" in raw_event, "Missing 'event' key"
            assert "data" in raw_event, "Missing 'data' key"
            assert isinstance(raw_event["event"], str)
            assert isinstance(raw_event["data"], str)

            parsed = json.loads(raw_event["data"])
            assert isinstance(parsed, dict)

    @pytest.mark.asyncio
    async def test_status_events_have_phase_field(self, orchestrator):
        events = await _collect_events(orchestrator.research("test query"))

        for e in events:
            if e["event"] == "status":
                assert "phase" in e["data"], f"Status event missing 'phase': {e}"

    @pytest.mark.asyncio
    async def test_token_events_have_content_field(self, orchestrator):
        events = await _collect_events(orchestrator.research("test query"))

        for e in events:
            if e["event"] == "token":
                assert "content" in e["data"], f"Token event missing 'content': {e}"
                assert isinstance(e["data"]["content"], str)

    @pytest.mark.asyncio
    async def test_source_complete_events_have_required_fields(self, orchestrator):
        events = await _collect_events(orchestrator.research("test query"))

        for e in events:
            if e["event"] == "source_complete":
                assert "source" in e["data"]
                assert "results_count" in e["data"]
                assert isinstance(e["data"]["results_count"], int)

    @pytest.mark.asyncio
    async def test_complete_event_has_required_fields(self, orchestrator):
        events = await _collect_events(orchestrator.research("test query"))

        complete = next(e for e in events if e["event"] == "complete")
        required_keys = {"session_id", "sources_used", "citations"}
        assert required_keys.issubset(complete["data"].keys())

    @pytest.mark.asyncio
    async def test_complete_citations_have_correct_structure(self, orchestrator):
        events = await _collect_events(orchestrator.research("test query"))

        complete = next(e for e in events if e["event"] == "complete")
        for citation in complete["data"]["citations"]:
            assert "id" in citation
            assert "url" in citation
            assert "source_name" in citation
            assert "title" in citation
            assert "relevance_score" in citation

    @pytest.mark.asyncio
    async def test_session_id_consistent_across_events(self, orchestrator):
        """The session_id from the first status event must match the complete event."""
        events = await _collect_events(orchestrator.research("test query"))

        first_status = events[0]
        complete = next(e for e in events if e["event"] == "complete")

        assert first_status["data"]["session_id"] == complete["data"]["session_id"]


# ---------------------------------------------------------------------------
# _resolve_adapters tests
# ---------------------------------------------------------------------------

class TestResolveAdapters:
    def test_none_sources_returns_all_available(self, orchestrator, source_registry_with_adapters):
        adapters = orchestrator._resolve_adapters(None)
        assert len(adapters) == 2

    def test_specific_source_name(self, orchestrator):
        adapters = orchestrator._resolve_adapters(["wikipedia"])
        assert len(adapters) == 1
        assert adapters[0].name == "wikipedia"

    def test_unknown_source_falls_back_to_all(self, orchestrator):
        adapters = orchestrator._resolve_adapters(["nonexistent"])
        assert len(adapters) == 2

    def test_mix_valid_and_invalid(self, orchestrator):
        adapters = orchestrator._resolve_adapters(["wikipedia", "nonexistent"])
        assert len(adapters) == 1
        assert adapters[0].name == "wikipedia"

    def test_unavailable_adapter_skipped(self):
        registry = SourceRegistry()
        registry.register(FakeAdapter(name="offline", display_name="Offline", available=False))
        registry.register(FakeAdapter(name="online", display_name="Online", available=True))

        orch = ResearchOrchestrator(
            query_analyzer=MagicMock(),
            source_registry=registry,
            ingestion_pipeline=MagicMock(),
            vector_store=MagicMock(),
            embedder=MagicMock(),
            synthesizer=MagicMock(),
        )

        adapters = orch._resolve_adapters(["offline", "online"])
        assert len(adapters) == 1
        assert adapters[0].name == "online"


# ---------------------------------------------------------------------------
# _safe_search tests
# ---------------------------------------------------------------------------

class TestSafeSearch:
    @pytest.mark.asyncio
    async def test_successful_search_returns_results(self):
        results = [_make_source_result(source_name="test")]
        adapter = FakeAdapter(name="test", display_name="Test", results=results)

        outcome = await ResearchOrchestrator._safe_search(adapter, "query", 5)

        assert outcome["source"] == "test"
        assert len(outcome["results"]) == 1
        assert outcome["error"] is None

    @pytest.mark.asyncio
    async def test_failed_search_returns_empty_with_error(self):
        adapter = FakeAdapter(
            name="broken", display_name="Broken",
            error=ConnectionError("refused"),
        )

        outcome = await ResearchOrchestrator._safe_search(adapter, "query", 5)

        assert outcome["source"] == "broken"
        assert outcome["results"] == []
        assert "refused" in outcome["error"]
