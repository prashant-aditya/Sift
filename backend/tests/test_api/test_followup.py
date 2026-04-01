from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import UUID

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine

from app.api.routes.research import router as research_router
from app.api.routes.sessions import router as sessions_router
from app.core.context_manager import ContextManager
from app.db.models import Base
from app.db.session import create_engine, create_sessionmaker
from app.db.vector_store import RetrievedChunk
from app.ingestion.chunker import Chunk
from app.sources.base import SourceAdapter, SourceResult
from app.sources.registry import SourceRegistry


def _parse_sse(body: str) -> list[dict]:
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
                events.append({"event": event_name, "data": json.loads(data_str)})
            event_name = None
            data_lines = []
    return events


class _FakeAdapter(SourceAdapter):
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


async def _init_db(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@pytest_asyncio.fixture()
async def app_with_db(tmp_path):
    db_path = tmp_path / "test.db"
    db_url = f"sqlite+aiosqlite:///{db_path}"

    app = FastAPI()
    app.include_router(research_router)
    app.include_router(sessions_router)

    class _S:
        database_url = db_url

    engine: AsyncEngine = create_engine(_S())  # type: ignore[arg-type]
    sm = create_sessionmaker(engine)
    await _init_db(engine)

    app.state.db_engine = engine
    app.state.db_sessionmaker = sm

    # Mock pipeline services needed by /research + /followup
    qa = type("QA", (), {})()

    async def _decompose(_q: str):
        return ["subq"]

    qa.decompose = _decompose

    registry = SourceRegistry()
    registry.register(_FakeAdapter())

    class _Pipeline:
        async def process(self, _results):
            return [
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
                )
            ]

    class _VS:
        def __init__(self):
            self.query_session_calls: list[str] = []

        def upsert_chunks(self, *_a, **_kw):
            return 1

        def query_session(self, session_id: str, query_embedding, n_results: int = 10, where=None):
            self.query_session_calls.append(session_id)
            return [
                RetrievedChunk(
                    chunk=Chunk(
                        chunk_id="c1",
                        text="Corpus content (session-scoped).",
                        source_url="https://example.com/fake",
                        source_name="fake",
                        source_title="Fake Result",
                        chunk_index=0,
                        total_chunks=1,
                        fetched_at=datetime.now(timezone.utc),
                        embedding=[0.1] * 384,
                    ),
                    score=0.9,
                    citation_id="fake:c1",
                )
            ]

    class _Embedder:
        async def embed(self, *_a, **_kw):
            return [[0.1] * 384]

    class _Synth:
        async def synthesize(self, *_a, **_kw):
            for t in ["Hello ", "world ", "[1]."]:
                yield t

    app.state.query_analyzer = qa
    app.state.source_registry = registry
    app.state.ingestion_pipeline = _Pipeline()
    app.state.vector_store = _VS()
    app.state.embedder = _Embedder()
    app.state.synthesizer = _Synth()

    async def _fake_summary(_t: str) -> str:
        return "SUMMARY"

    app.state.context_manager = ContextManager(summarizer=_fake_summary, max_context_tokens=10_000)

    yield app
    await engine.dispose()


class TestFollowupEndpoint:
    @pytest.mark.asyncio
    async def test_followup_reuses_session_and_creates_second_turn(self, app_with_db):
        async with AsyncClient(
            transport=ASGITransport(app=app_with_db), base_url="http://test"
        ) as client:
            resp = await client.post("/api/v1/research", json={"query": "Topic A"})
            assert resp.status_code == 200
            session_id = UUID(
                str(next(e for e in _parse_sse(resp.text) if e["event"] == "complete")["data"]["session_id"])
            )

            follow = await client.post(
                f"/api/v1/research/{session_id}/followup",
                json={"query": "Follow-up Q"},
            )
            assert follow.status_code == 200
            follow_events = _parse_sse(follow.text)
            complete = next(e for e in follow_events if e["event"] == "complete")
            assert UUID(str(complete["data"]["session_id"])) == session_id

            got = await client.get(f"/api/v1/sessions/{session_id}")
            assert got.status_code == 200
            body = got.json()
            assert len(body["turns"]) == 2
            assert body["turns"][1]["query"] == "Follow-up Q"

        # Dense retrieval must have been queried against the same session collection.
        vs = app_with_db.state.vector_store
        assert vs.query_session_calls, "Expected dense retrieval to query the session collection"
        assert vs.query_session_calls[-1] == str(session_id)

