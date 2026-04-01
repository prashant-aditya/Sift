"""Research session CRUD endpoints (PostgreSQL-backed)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.dependencies import get_current_user
from app.db.models import ResearchSession, ResearchTurn
from app.db.models import User

router = APIRouter(prefix="/api/v1", tags=["sessions"])


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _require_sessionmaker(request: Request) -> async_sessionmaker[AsyncSession]:
    sm = getattr(request.app.state, "db_sessionmaker", None)
    if sm is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not configured",
        )
    return sm


async def _db(request: Request) -> AsyncIterator[AsyncSession]:
    sm = _require_sessionmaker(request)
    async with sm() as session:
        yield session


class SessionListItem(BaseModel):
    id: UUID
    name: str
    status: str
    created_at: datetime
    updated_at: datetime


class TurnOut(BaseModel):
    id: UUID
    query: str
    answer: str
    citations: list[dict[str, Any]]
    metrics: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class SessionOut(BaseModel):
    id: UUID
    name: str
    status: str
    created_at: datetime
    updated_at: datetime
    turns: list[TurnOut]


class PageMeta(BaseModel):
    page: int
    per_page: int


class SessionListResponse(BaseModel):
    data: list[SessionListItem]
    meta: PageMeta


class SessionRenameRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    request: Request,
    user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    include_archived: bool = Query(False),
    db: AsyncSession = Depends(_db),
) -> SessionListResponse:
    stmt = select(ResearchSession).where(ResearchSession.user_id == user.id)
    if not include_archived:
        stmt = stmt.where(ResearchSession.status != "archived")
    stmt = (
        stmt.order_by(desc(ResearchSession.updated_at))
        .limit(per_page)
        .offset((page - 1) * per_page)
    )

    rows = (await db.execute(stmt)).scalars().all()
    return SessionListResponse(
        data=[
            SessionListItem(
                id=r.id,
                name=r.name,
                status=r.status,
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
            for r in rows
        ],
        meta=PageMeta(page=page, per_page=per_page),
    )


@router.get("/sessions/{session_id}", response_model=SessionOut)
async def get_session(
    session_id: UUID,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(_db),
) -> SessionOut:
    session = await db.get(ResearchSession, session_id)
    if session is None or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="Session not found")

    turns_stmt = (
        select(ResearchTurn)
        .where(ResearchTurn.session_id == session_id)
        .order_by(ResearchTurn.created_at.asc())
    )
    turns = (await db.execute(turns_stmt)).scalars().all()

    return SessionOut(
        id=session.id,
        name=session.name,
        status=session.status,
        created_at=session.created_at,
        updated_at=session.updated_at,
        turns=[
            TurnOut(
                id=t.id,
                query=t.query,
                answer=t.answer,
                citations=t.citations or [],
                metrics=t.metrics or {},
                created_at=t.created_at,
                updated_at=t.updated_at,
            )
            for t in turns
        ],
    )


@router.patch("/sessions/{session_id}", response_model=SessionOut)
async def rename_session(
    session_id: UUID,
    body: SessionRenameRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(_db),
) -> SessionOut:
    session = await db.get(ResearchSession, session_id)
    if session is None or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="Session not found")

    session.name = body.name
    session.updated_at = _utcnow()
    await db.commit()
    await db.refresh(session)
    return await get_session(session_id=session_id, request=request, user=user, db=db)


@router.delete("/sessions/{session_id}", status_code=204)
async def archive_session(
    session_id: UUID,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(_db),
) -> None:
    session = await db.get(ResearchSession, session_id)
    if session is None or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="Session not found")

    session.status = "archived"
    session.archived_at = _utcnow()
    session.updated_at = _utcnow()
    await db.commit()
    return None


class KnowledgeListResponse(BaseModel):
    data: list[dict]


@router.get("/knowledge", response_model=KnowledgeListResponse, tags=["knowledge"])
async def list_knowledge(
    _user: User = Depends(get_current_user),
) -> KnowledgeListResponse:
    # Placeholder: the knowledge feature will be implemented in a later goal.
    return KnowledgeListResponse(data=[])
