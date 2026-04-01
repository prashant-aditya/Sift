from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
import pytest_asyncio
import jwt
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine

from app.api.routes.research import router as research_router
from app.api.routes.sessions import router as sessions_router
from app.db.vector_store import RetrievedChunk
from app.db.models import Base
from app.db.session import create_engine, create_sessionmaker
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


@pytest_asyncio.fixture()
async def sessions_app(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    db_url = f"sqlite+aiosqlite:///{db_path}"
    app = FastAPI()
    app.include_router(research_router)
    app.include_router(sessions_router)

    monkeypatch.setenv("SUPABASE_JWT_SECRET", "test-secret")

    class _S:
        database_url = db_url

    engine: AsyncEngine = create_engine(_S())  # type: ignore[arg-type]
    sm = create_sessionmaker(engine)

    await _init_db(engine)

    app.state.db_engine = engine
    app.state.db_sessionmaker = sm

    # Mock pipeline services needed by /research
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
        def upsert_chunks(self, *_a, **_kw):
            return 1

        def query_session(
            self, session_id: str, query_embedding, n_results: int = 10, where=None
        ):
            return [
                RetrievedChunk(
                    chunk=Chunk(
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

    yield app
    await engine.dispose()


def _auth_headers(
    *, sub: str = "user-123", secret: str = "test-secret"
) -> dict[str, str]:
    token = jwt.encode(
        {"sub": sub, "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        secret,
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


async def _init_db(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


class TestSessionsCRUD:
    @pytest.mark.asyncio
    async def test_research_creates_session_and_turn(self, sessions_app):
        async with AsyncClient(
            transport=ASGITransport(app=sessions_app), base_url="http://test"
        ) as client:
            headers = _auth_headers()
            resp = await client.post(
                "/api/v1/research", json={"query": "What is Python?"}, headers=headers
            )
            assert resp.status_code == 200
            events = _parse_sse(resp.text)
            complete = next(e for e in events if e["event"] == "complete")
            session_id = UUID(str(complete["data"]["session_id"]))

            listed = await client.get("/api/v1/sessions", headers=headers)
            assert listed.status_code == 200
            ids = [UUID(item["id"]) for item in listed.json()["data"]]
            assert session_id in ids

            got = await client.get(f"/api/v1/sessions/{session_id}", headers=headers)
            assert got.status_code == 200
            body = got.json()
            assert UUID(body["id"]) == session_id
            assert len(body["turns"]) == 1
            assert body["turns"][0]["query"] == "What is Python?"
            assert "Hello world" in body["turns"][0]["answer"]

    @pytest.mark.asyncio
    async def test_rename_and_archive(self, sessions_app):
        async with AsyncClient(
            transport=ASGITransport(app=sessions_app), base_url="http://test"
        ) as client:
            headers = _auth_headers()
            resp = await client.post(
                "/api/v1/research", json={"query": "Topic A"}, headers=headers
            )
            session_id = UUID(
                str(
                    next(e for e in _parse_sse(resp.text) if e["event"] == "complete")[
                        "data"
                    ]["session_id"]
                )
            )

            renamed = await client.patch(
                f"/api/v1/sessions/{session_id}",
                json={"name": "My Session"},
                headers=headers,
            )
            assert renamed.status_code == 200
            assert renamed.json()["name"] == "My Session"

            archived = await client.delete(
                f"/api/v1/sessions/{session_id}", headers=headers
            )
            assert archived.status_code == 204

            listed = await client.get("/api/v1/sessions", headers=headers)
            assert listed.status_code == 200
            ids = [UUID(item["id"]) for item in listed.json()["data"]]
            assert session_id not in ids

            listed_all = await client.get(
                "/api/v1/sessions?include_archived=true", headers=headers
            )
            ids_all = [UUID(item["id"]) for item in listed_all.json()["data"]]
            assert session_id in ids_all

    @pytest.mark.asyncio
    async def test_pagination(self, sessions_app):
        async with AsyncClient(
            transport=ASGITransport(app=sessions_app), base_url="http://test"
        ) as client:
            headers = _auth_headers()
            for i in range(5):
                resp = await client.post(
                    "/api/v1/research", json={"query": f"Q{i} here"}, headers=headers
                )
                assert resp.status_code == 200

            p1 = await client.get("/api/v1/sessions?page=1&per_page=2", headers=headers)
            assert p1.status_code == 200
            assert len(p1.json()["data"]) == 2
            assert p1.json()["meta"]["page"] == 1
            assert p1.json()["meta"]["per_page"] == 2

            p2 = await client.get("/api/v1/sessions?page=2&per_page=2", headers=headers)
            assert p2.status_code == 200
            assert len(p2.json()["data"]) == 2
