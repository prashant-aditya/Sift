"""LLM synthesis engine for generating cited answers from retrieved chunks.

Accepts a list of :class:`RetrievedChunk` objects and the original user query,
then streams a structured, cited answer token-by-token via the Groq API.
Citations use numeric IDs (``[1]``, ``[2]``, …) that map back to the
retrieved source chunks.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any

from pydantic import BaseModel
from groq import AsyncGroq

from app.config import get_settings
from app.db.vector_store import RetrievedChunk

logger = logging.getLogger(__name__)

SYNTHESIS_SYSTEM_PROMPT = """\
You are a research synthesis engine.  Your task is to produce a comprehensive,
well-structured answer to the user's query using ONLY the provided source
chunks.

Rules:
- Cite sources using their numeric IDs in square brackets: [1], [2], etc.
- You may ONLY reference source IDs listed under "Sources" below.
  Do NOT invent or fabricate any citation.
- Do NOT generate URLs or links — the frontend resolves citation IDs to URLs.
- If sources contain contradicting information, acknowledge the contradiction
  and analyze the conditions under which each claim holds.
- Structure your answer with clear sections when the topic warrants it.
- If no relevant source chunks are provided, state clearly that insufficient
  information is available to answer the query.
- Be concise but thorough.  Prioritise accuracy over length."""

NO_SOURCES_RESPONSE = (
    "I don't have enough information from the retrieved sources to answer "
    "this query.  Try broadening your search or enabling additional sources."
)

DEFAULT_TEMPERATURE = 0.3
DEFAULT_MAX_TOKENS = 2048


class CitationMapping(BaseModel):
    """Maps a numeric citation ID to its source metadata."""

    citation_id: int
    source_url: str
    source_name: str
    source_title: str
    original_citation_id: str


class SynthesisResult(BaseModel):
    """Container for a completed (non-streaming) synthesis."""

    answer: str
    citations: list[CitationMapping]


class Synthesizer:
    """Generates cited, streaming answers from retrieved chunks via Groq.

    Parameters
    ----------
    api_key:
        Groq API key.  Falls back to ``Settings.groq_api_key``.
    model:
        Chat model identifier.  Falls back to ``Settings.llm_model``.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        settings = get_settings()
        self._api_key = api_key or settings.groq_api_key
        self._model = model or settings.llm_model
        self._client = AsyncGroq(api_key=self._api_key)

    async def synthesize(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        *,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> AsyncIterator[str]:
        """Stream a cited answer token-by-token.

        Yields individual string tokens as they arrive from the LLM.
        If *chunks* is empty, yields a single message explaining the lack of
        information without calling the LLM.
        """
        if not chunks:
            yield NO_SOURCES_RESPONSE
            return

        user_message = _build_user_message(query, chunks)

        stream = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": SYNTHESIS_SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content

    async def synthesize_complete(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        *,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> SynthesisResult:
        """Return the full answer and citation map (non-streaming convenience)."""
        tokens: list[str] = []
        async for token in self.synthesize(
            query,
            chunks,
            temperature=temperature,
            max_tokens=max_tokens,
        ):
            tokens.append(token)

        return SynthesisResult(
            answer="".join(tokens),
            citations=build_citation_map(chunks),
        )

    @staticmethod
    def build_citation_map(chunks: list[RetrievedChunk]) -> list[CitationMapping]:
        """Public accessor for the citation mapping."""
        return build_citation_map(chunks)


def build_citation_map(chunks: list[RetrievedChunk]) -> list[CitationMapping]:
    """Create the numeric-ID → source-metadata mapping for a chunk list."""
    return [
        CitationMapping(
            citation_id=idx + 1,
            source_url=rc.chunk.source_url,
            source_name=rc.chunk.source_name,
            source_title=rc.chunk.source_title,
            original_citation_id=rc.citation_id,
        )
        for idx, rc in enumerate(chunks)
    ]


def _build_user_message(query: str, chunks: list[RetrievedChunk]) -> str:
    """Format the user prompt with numbered source blocks."""
    source_blocks: list[str] = []
    for idx, rc in enumerate(chunks, start=1):
        header = f"[{idx}] (source: {rc.chunk.source_name} — {rc.chunk.source_title})"
        source_blocks.append(f"{header}\n{rc.chunk.text}")

    sources_text = "\n\n".join(source_blocks)

    return f"Sources:\n{sources_text}\n\nQuery: {query}"
