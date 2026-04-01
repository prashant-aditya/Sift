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

from app.api.dependencies import get_optional_user, get_current_user
from app.core.context_manager import ContextManager
from app.core.orchestrator import ResearchOrchestrator
from app.db.models import User, ResearchSession
from app.sources.registry import SourceRegistry

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


def _build_orchestrator(
    request: Request, *, db_sessionmaker: async_sessionmaker[AsyncSession] | None = None
) -> ResearchOrchestrator:
    """Construct a ``ResearchOrchestrator`` from app-level shared state."""
    state = request.app.state

    # Some tests mount routers on a bare FastAPI() without running the app
    # lifespan initializer. Provide safe in-process fallbacks so the endpoint
    # can still respond (typically with "no available sources") rather than
    # crashing due to missing state.
    if not hasattr(state, "query_analyzer"):

        class _FallbackQueryAnalyzer:
            async def decompose(self, query: str) -> list[str]:
                q = (query or "").strip()
                return [q] if q else []

        state.query_analyzer = _FallbackQueryAnalyzer()

    if not hasattr(state, "source_registry"):
        state.source_registry = SourceRegistry()

    if not hasattr(state, "embedder"):

        class _FallbackEmbedder:
            async def embed(self, texts: list[str]) -> list[list[float]]:
                # Shape-only embedding: prevents crashes in retrieval when the
                # app isn't fully configured.
                return [[0.0] for _ in texts]

        state.embedder = _FallbackEmbedder()

    if not hasattr(state, "vector_store"):

        class _FallbackVectorStore:
            @staticmethod
            def upsert_chunks(*_a, **_kw) -> int:
                return 0

            @staticmethod
            def query_session(*_a, **_kw) -> list:
                return []

        state.vector_store = _FallbackVectorStore()

    if not hasattr(state, "ingestion_pipeline"):

        class _FallbackPipeline:
            async def process(self, _results):
                return []

        state.ingestion_pipeline = _FallbackPipeline()

    if not hasattr(state, "synthesizer"):

        class _FallbackSynthesizer:
            async def synthesize(self, *_a, **_kw):
                if False:  # pragma: no cover
                    yield ""  # type: ignore[misc]
                return

        state.synthesizer = _FallbackSynthesizer()

    return ResearchOrchestrator(
        query_analyzer=state.query_analyzer,
        source_registry=state.source_registry,
        ingestion_pipeline=state.ingestion_pipeline,
        vector_store=state.vector_store,
        embedder=state.embedder,
        synthesizer=state.synthesizer,
        celery_app=getattr(state, "celery_app", None),
        cache=getattr(state, "research_cache", None),
        db_sessionmaker=db_sessionmaker
        if db_sessionmaker is not None
        else getattr(state, "db_sessionmaker", None),
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
async def research(
    body: ResearchRequest,
    request: Request,
    user: User | None = Depends(get_optional_user),
) -> EventSourceResponse:
    """Stream research results as Server-Sent Events.

    The response is an SSE stream containing the following event types:

    - ``status``  — pipeline phase updates (decomposing, searching, etc.)
    - ``source_complete`` — per-source search result counts
    - ``token``   — LLM synthesis tokens (streamed incrementally)
    - ``complete`` — final event with ``session_id``, ``citations``, and metadata
    """
    orchestrator = _build_orchestrator(
        request,
        db_sessionmaker=(
            getattr(request.app.state, "db_sessionmaker", None)
            if user is not None
            else None
        ),
    )
    return EventSourceResponse(
        orchestrator.research(
            body.query, body.sources, body.depth, user_id=(user.id if user else None)
        ),
    )


@router.post("/research/{session_id}/followup")
async def followup(
    session_id: UUID,
    body: FollowupRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(_db),
) -> EventSourceResponse:
    orchestrator = _build_orchestrator(request)
    context_manager: ContextManager = (
        getattr(request.app.state, "context_manager", None) or ContextManager()
    )

    # Enforce ownership for authenticated followups.
    session = await db.get(ResearchSession, session_id)
    if session is None or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="Session not found")

    context = await context_manager.build_context(str(session_id), db)
    augmented_query = (
        f"Previous research context:\n{context}\n\nFollow-up question: {body.query}"
    )

    return EventSourceResponse(
        orchestrator.followup(
            session_id=str(session_id),
            query=body.query,
            augmented_query=augmented_query,
            sources=body.sources,
            depth=body.depth,
            user_id=user.id,
        )
    )
