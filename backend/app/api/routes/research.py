"""SSE-streaming research endpoint.

Accepts a research query and streams Server-Sent Events through the full
pipeline: decomposition → multi-source search → ingestion → retrieval →
LLM synthesis.
"""

from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

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
