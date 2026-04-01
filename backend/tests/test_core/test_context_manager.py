from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from uuid import UUID

from app.core.context_manager import ContextManager
from app.db.models import Base, ResearchSession, ResearchTurn
from app.db.session import create_engine, create_sessionmaker


async def _init_db(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@pytest_asyncio.fixture()
async def db(tmp_path):
    db_path = tmp_path / "ctx.db"
    db_url = f"sqlite+aiosqlite:///{db_path}"

    class _S:
        database_url = db_url

    engine: AsyncEngine = create_engine(_S())  # type: ignore[arg-type]
    sm = create_sessionmaker(engine)
    await _init_db(engine)

    async with sm() as session:
        yield session
    await engine.dispose()


async def _seed_turns(db: AsyncSession, n: int) -> str:
    sid = uuid4()
    db.add(ResearchSession(id=sid, name="Test", status="active"))
    await db.commit()

    for i in range(n):
        db.add(
            ResearchTurn(
                id=uuid4(),
                session_id=sid,
                query=f"Q{i}?",
                answer=f"A{i}. " + ("lorem ipsum " * 20),
                citations=[],
                metrics={},
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
        )
    await db.commit()
    return str(sid)


class TestContextManager:
    @pytest.mark.asyncio
    async def test_build_context_full_for_1_turn(self, db):
        session_id = await _seed_turns(db, 1)
        cm = ContextManager(
            summarizer=lambda _t: pytest.fail("summarizer should not be called"),
            max_context_tokens=10_000,
        )
        ctx = await cm.build_context(session_id, db)
        assert "Turn 1" in ctx
        assert "User: Q0?" in ctx

    @pytest.mark.asyncio
    async def test_build_context_full_for_5_turns(self, db):
        session_id = await _seed_turns(db, 5)
        cm = ContextManager(
            summarizer=lambda _t: pytest.fail("summarizer should not be called"),
            max_context_tokens=10_000,
        )
        ctx = await cm.build_context(session_id, db)
        assert "Turn 1" in ctx and "Turn 5" in ctx

    @pytest.mark.asyncio
    async def test_build_context_full_for_10_turns(self, db):
        session_id = await _seed_turns(db, 10)
        cm = ContextManager(
            summarizer=lambda _t: pytest.fail("summarizer should not be called"),
            max_context_tokens=10_000,
        )
        ctx = await cm.build_context(session_id, db)
        assert "Turn 10" in ctx

    @pytest.mark.asyncio
    async def test_compression_triggers_and_caches_summary(self, db):
        session_id = await _seed_turns(db, 6)

        async def _fake_summary(_t: str) -> str:
            return "SUMMARY: key findings; contradictions; preferences."

        cm = ContextManager(summarizer=_fake_summary, max_context_tokens=50)
        ctx = await cm.build_context(session_id, db)
        assert "Session summary (compressed):" in ctx
        assert "Most recent turns (verbatim):" in ctx
        assert "SUMMARY:" in ctx

        # Ensure compressed_context cached on an older anchor turn.
        from sqlalchemy import select

        turns = (
            await db.execute(
                select(ResearchTurn)
                .where(ResearchTurn.session_id == UUID(session_id))
                .order_by(ResearchTurn.created_at.asc())
            )
        ).scalars().all()
        assert any((t.compressed_context or "").startswith("SUMMARY:") for t in turns[:-2])

