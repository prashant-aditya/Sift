"""API endpoint tests for /api/v1/health and /api/v1/research.

Covers:
  - Health check endpoint
  - Valid research request with SSE streaming
  - Invalid request validation (missing / too-short query, bad depth)
  - SSE event format correctness
  - Concurrent request handling
"""

from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.routes.health import router as health_router
from app.api.routes.research import router as research_router
from app.db.vector_store import RetrievedChunk
from app.ingestion.chunker import Chunk
from app.sources.base import SourceAdapter, SourceResult
from app.sources.registry import SourceRegistry


# ---------------------------------------------------------------------------
# SSE response parser
# ---------------------------------------------------------------------------


def _parse_sse(body: str) -> list[dict]:
    """Parse raw SSE text into a list of ``{event, data}`` dicts."""
    events: list[dict] = []
    event_name: str | None = None
    data_lines: list[str] = []

    for line in body.split("\n"):
        line = line.rstrip("\r")
        if line.startswith("event:"):
            event_name = line[len("event:") :].strip()
        elif line.startswith("data:"):
            data_lines.append(line[len("data:") :].strip())
        elif line == "":
            if event_name is not None and data_lines:
                data_str = "\n".join(data_lines)
                try:
                    data = json.loads(data_str)
                except json.JSONDecodeError:
                    data = data_str
                events.append({"event": event_name, "data": data})
            event_name = None
            data_lines = []

    return events


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _make_retrieved_chunk(
    text: str = "Test chunk text",
    chunk_id: str = "chunk-001",
    source_name: str = "fake",
    source_url: str = "https://example.com/fake",
    source_title: str = "Fake Result",
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
            embedding=[0.1] * 384,
        ),
        score=score,
        citation_id=f"{source_name}:{chunk_id[:8]}",
    )


class _FakeAdapter(SourceAdapter):
    """Controllable adapter that returns canned results."""

    name = "fake"
    display_name = "Fake Source"

    async def search(self, query, max_results=None):
        return [
            SourceResult(
                title="Fake Result",
                url="https://example.com/fake",
                snippet="A fake search result.",
                source_name=self.name,
            )
        ]

    def is_available(self):
        return True


@asynccontextmanager
async def _noop_lifespan(app: FastAPI):
    yield


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def test_app():
    """Create a minimal FastAPI app with fully mocked pipeline services."""
    app = FastAPI(lifespan=_noop_lifespan)
    app.include_router(health_router)
    app.include_router(research_router)

    qa = MagicMock()
    qa.decompose = AsyncMock(return_value=["test sub-query"])

    registry = SourceRegistry()
    registry.register(_FakeAdapter())

    pipeline = MagicMock()
    pipeline.process = AsyncMock(
        return_value=[
            Chunk(
                chunk_id="c1",
                text="Ingested content.",
                source_url="https://example.com/fake",
                source_name="fake",
                source_title="Fake Result",
                chunk_index=0,
                total_chunks=1,
                fetched_at=datetime.now(timezone.utc),
                embedding=[0.1] * 384,
            ),
        ]
    )

    vs = MagicMock()
    vs.upsert_chunks = MagicMock(return_value=1)
    vs.query_session = MagicMock(return_value=[_make_retrieved_chunk()])

    embedder = MagicMock()
    embedder.embed = AsyncMock(return_value=[[0.1] * 384])

    synth = MagicMock()

    async def _fake_synth(query, chunks, **kw):
        for token in ["Hello ", "world ", "[1]."]:
            yield token

    synth.synthesize = _fake_synth

    app.state.query_analyzer = qa
    app.state.source_registry = registry
    app.state.ingestion_pipeline = pipeline
    app.state.vector_store = vs
    app.state.embedder = embedder
    app.state.synthesizer = synth

    return app


# ======================================================================
# Health endpoint
# ======================================================================


class TestHealthEndpoint:
    async def test_health_returns_ok(self, test_app):
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/health")

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert "version" in body


# ======================================================================
# Research endpoint — valid requests
# ======================================================================


class TestResearchValidRequest:
    async def test_returns_200_with_sse_content_type(self, test_app):
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/research", json={"query": "What is Python?"}
            )

        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers.get("content-type", "")

    async def test_sse_stream_contains_required_events(self, test_app):
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/research", json={"query": "What is Python?"}
            )

        events = _parse_sse(resp.text)
        event_types = [e["event"] for e in events]

        assert "status" in event_types
        assert "token" in event_types
        assert "complete" in event_types

    async def test_complete_event_has_session_id(self, test_app):
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/research", json={"query": "What is Python?"}
            )

        events = _parse_sse(resp.text)
        complete = next(e for e in events if e["event"] == "complete")

        assert "session_id" in complete["data"]
        UUID(str(complete["data"]["session_id"]))


# ======================================================================
# Research endpoint — invalid requests
# ======================================================================


class TestResearchInvalidRequest:
    async def test_missing_query_returns_422(self, test_app):
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.post("/api/v1/research", json={})

        assert resp.status_code == 422

    async def test_query_too_short_returns_422(self, test_app):
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.post("/api/v1/research", json={"query": "ab"})

        assert resp.status_code == 422

    async def test_invalid_depth_returns_422(self, test_app):
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/research",
                json={"query": "Valid query here", "depth": "ultradeep"},
            )

        assert resp.status_code == 422


# ======================================================================
# SSE format correctness
# ======================================================================


class TestSSEFormat:
    async def test_all_events_have_parseable_json_data(self, test_app):
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/research", json={"query": "What is Python?"}
            )

        events = _parse_sse(resp.text)
        assert len(events) > 0
        for event in events:
            assert isinstance(event["event"], str)
            assert isinstance(event["data"], dict)


# ======================================================================
# Concurrent requests
# ======================================================================


class TestConcurrentRequests:
    async def test_concurrent_requests_succeed_independently(self, test_app):
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            tasks = [
                client.post(
                    "/api/v1/research",
                    json={"query": f"Query about topic {i}"},
                )
                for i in range(3)
            ]
            responses = await asyncio.gather(*tasks)

        for resp in responses:
            assert resp.status_code == 200
            events = _parse_sse(resp.text)
            event_types = [e["event"] for e in events]
            assert "complete" in event_types
