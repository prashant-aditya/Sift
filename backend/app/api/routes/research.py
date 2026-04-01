"""SSE-streaming research endpoint.

Accepts a research query and streams Server-Sent Events through the full
pipeline: decomposition → multi-source search → ingestion → retrieval →
LLM synthesis.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.context_manager import ContextManager
from app.core.orchestrator import ResearchOrchestrator

router = APIRouter(prefix="/api/v1", tags=["research"])


class ResearchRequest(BaseModel):
    """Validated request body for the research endpoint."""

    query: str = Field(..., min_length=3, max_length=2000)
    sources: Optional[list[str]] = Field(
        default=None,
        description="Source adapter names to search. None uses all available.",
    )
    depth: Literal["quick", "standard", "deep"] = Field(
        default="standard",
        description="Controls max results per source and retrieval depth.",
    )


class Citation(BaseModel):
    """Citation reference included in the ``complete`` SSE event."""

    id: int
    title: str
    url: str
    source_name: str
    relevance_score: float


def _build_orchestrator(request: Request) -> ResearchOrchestrator:
    """Construct a ``ResearchOrchestrator`` from app-level shared state."""
    state = request.app.state
    return ResearchOrchestrator(
        query_analyzer=state.query_analyzer,
        source_registry=state.source_registry,
        ingestion_pipeline=state.ingestion_pipeline,
        vector_store=state.vector_store,
        embedder=state.embedder,
        synthesizer=state.synthesizer,
        celery_app=getattr(state, "celery_app", None),
        cache=getattr(state, "research_cache", None),
        db_sessionmaker=getattr(state, "db_sessionmaker", None),
    )


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


class FollowupRequest(BaseModel):
    """Validated request body for a follow-up query within a session."""

    query: str = Field(..., min_length=3, max_length=2000)
    sources: Optional[list[str]] = Field(
        default=None,
        description="Source adapter names to search. None uses all available.",
    )
    depth: Literal["quick", "standard", "deep"] = Field(
        default="standard",
        description="Controls max results per source and retrieval depth.",
    )


@router.post("/research")
async def research(body: ResearchRequest, request: Request) -> EventSourceResponse:
    """Stream research results as Server-Sent Events.

    The response is an SSE stream containing the following event types:

    - ``status``  — pipeline phase updates (decomposing, searching, etc.)
    - ``source_complete`` — per-source search result counts
    - ``token``   — LLM synthesis tokens (streamed incrementally)
    - ``complete`` — final event with ``session_id``, ``citations``, and metadata
    """
    orchestrator = _build_orchestrator(request)
    return EventSourceResponse(
        orchestrator.research(body.query, body.sources, body.depth),
    )


@router.post("/research/{session_id}/followup")
async def followup(
    session_id: UUID,
    body: FollowupRequest,
    request: Request,
    db: AsyncSession = Depends(_db),
) -> EventSourceResponse:
    orchestrator = _build_orchestrator(request)
    context_manager: ContextManager = getattr(request.app.state, "context_manager", None) or ContextManager()

    context = await context_manager.build_context(str(session_id), db)
    augmented_query = (
        "Previous research context:\n"
        f"{context}\n\n"
        f"Follow-up question: {body.query}"
    )

    return EventSourceResponse(
        orchestrator.followup(
            session_id=str(session_id),
            query=body.query,
            augmented_query=augmented_query,
            sources=body.sources,
            depth=body.depth,
        )
    )
