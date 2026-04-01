from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine

from app.api.routes.research import router as research_router
from app.api.routes.sessions import router as sessions_router
from app.db.models import Base
from app.db.session import create_engine, create_sessionmaker


def _bearer(payload: dict, *, secret: str) -> str:
    token = jwt.encode(payload, secret, algorithm="HS256")
    return f"Bearer {token}"


@pytest_asyncio.fixture()
async def app_with_db(tmp_path, monkeypatch):
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "test-secret")

    db_path = tmp_path / "test.db"
    db_url = f"sqlite+aiosqlite:///{db_path}"

    app = FastAPI()
    app.include_router(research_router)
    app.include_router(sessions_router)

    class _S:
        database_url = db_url

    engine: AsyncEngine = create_engine(_S())  # type: ignore[arg-type]
    sm = create_sessionmaker(engine)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    app.state.db_engine = engine
    app.state.db_sessionmaker = sm

    yield app
    await engine.dispose()


class TestSupabaseAuth:
    @pytest.mark.asyncio
    async def test_sessions_requires_auth(self, app_with_db):
        async with AsyncClient(
            transport=ASGITransport(app=app_with_db), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/sessions")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_token_rejected(self, app_with_db):
        async with AsyncClient(
            transport=ASGITransport(app=app_with_db), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/v1/sessions", headers={"Authorization": "Bearer not-a-jwt"}
            )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_expired_token_rejected(self, app_with_db):
        secret = "test-secret"
        auth = _bearer(
            {"sub": "user-1", "exp": datetime.now(timezone.utc) - timedelta(seconds=1)},
            secret=secret,
        )
        async with AsyncClient(
            transport=ASGITransport(app=app_with_db), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/sessions", headers={"Authorization": auth})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_valid_token_allows_sessions_endpoint(self, app_with_db):
        secret = "test-secret"
        auth = _bearer(
            {"sub": "user-1", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            secret=secret,
        )
        async with AsyncClient(
            transport=ASGITransport(app=app_with_db), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/sessions", headers={"Authorization": auth})
        assert resp.status_code == 200
        assert "data" in resp.json()

    @pytest.mark.asyncio
    async def test_anonymous_research_still_works(self, app_with_db):
        # Anonymous mode is allowed for /research and should not error on missing auth.
        async with AsyncClient(
            transport=ASGITransport(app=app_with_db), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/research", json={"query": "What is Python?"}
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_knowledge_requires_auth(self, app_with_db):
        async with AsyncClient(
            transport=ASGITransport(app=app_with_db), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/knowledge")
        assert resp.status_code == 401
