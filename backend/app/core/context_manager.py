"""Session context builder with progressive summarization.

This module provides a DB-backed ``ContextManager`` used by follow-up queries.
It keeps recent turns verbatim while compressing older turns into a concise
summary stored on the most recent turn included in that summary.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from google import genai
from google.genai import types
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import ResearchSession, ResearchTurn

logger = logging.getLogger(__name__)


class ContextManager:
    """Manages growing research session context with progressive summarization."""

    MAX_CONTEXT_TOKENS = 4096
    SUMMARY_TOKEN_BUDGET = 500

    def __init__(
        self,
        *,
        summarizer: Optional[Callable[[str], Awaitable[str]]] = None,
        max_context_tokens: int | None = None,
    ) -> None:
        self._summarizer = summarizer or self._default_summarizer()
        self._max_context_tokens = max_context_tokens or self.MAX_CONTEXT_TOKENS

    async def build_context(self, session_id: str, db: AsyncSession) -> str:
        """Return session context string (full or compressed to fit budget)."""
        sid = _parse_session_id(session_id)

        session = await db.get(ResearchSession, sid)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")

        turns = await self._get_session_turns(sid, db)
        if not turns:
            return ""

        full_context = self._format_full_context(turns)
        if self._estimate_tokens(full_context) <= self._max_context_tokens:
            return full_context

        return await self._compress_older_turns(turns, db)

    async def _get_session_turns(
        self, sid: UUID, db: AsyncSession
    ) -> list[ResearchTurn]:
        stmt = (
            select(ResearchTurn)
            .where(ResearchTurn.session_id == sid)
            .order_by(ResearchTurn.created_at.asc())
        )
        return (await db.execute(stmt)).scalars().all()

    def _format_full_context(self, turns: list[ResearchTurn]) -> str:
        blocks: list[str] = []
        for i, t in enumerate(turns, start=1):
            blocks.append(
                "\n".join(
                    [
                        f"Turn {i}",
                        f"User: {t.query}",
                        f"Assistant: {t.answer}",
                    ]
                )
            )
        return "\n\n".join(blocks)

    async def _compress_older_turns(
        self, turns: list[ResearchTurn], db: AsyncSession
    ) -> str:
        if len(turns) <= 2:
            # Nothing to keep aside from the latest turns; fall back to truncation.
            return self._format_full_context(turns[-2:])

        recent = turns[-2:]
        older = turns[:-2]

        cached_turn = next(
            (t for t in reversed(older) if (t.compressed_context or "").strip()), None
        )
        if cached_turn is not None:
            summary = str(cached_turn.compressed_context or "").strip()
        else:
            text_to_summarize = self._format_full_context(older)
            summary = (await self._summarizer(text_to_summarize)).strip()
            if summary:
                # Cache on the last older turn (progressive summarization anchor).
                anchor = older[-1]
                anchor.compressed_context = summary
                try:
                    await db.commit()
                except Exception:
                    await db.rollback()
                    logger.exception("Failed to cache compressed_context")

        recent_text = self._format_full_context(recent)
        compressed = "\n\n".join(
            [
                "Session summary (compressed):",
                summary or "(summary unavailable)",
                "",
                "Most recent turns (verbatim):",
                recent_text,
            ]
        ).strip()

        # If the summary is still too big (rare), clip the summary portion.
        if self._estimate_tokens(compressed) > self._max_context_tokens and summary:
            clipped = _clip_to_token_budget(summary, self._max_context_tokens // 2)
            compressed = "\n\n".join(
                [
                    "Session summary (compressed):",
                    clipped,
                    "",
                    "Most recent turns (verbatim):",
                    recent_text,
                ]
            ).strip()

        return compressed

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        # Heuristic: ~4 characters per token for English-ish text.
        # Avoids adding a tokenizer dependency.
        t = (text or "").strip()
        if not t:
            return 0
        return max(1, len(t) // 4)

    @classmethod
    def _default_summarizer(cls) -> Callable[[str], Awaitable[str]]:
        settings = get_settings()
        provider = (settings.llm_provider or "google").lower()
        if provider != "google":
            # Keep the default summarizer dependency-light; tests inject a fake.
            async def _fallback(text: str) -> str:
                return _clip_to_token_budget(text, cls.SUMMARY_TOKEN_BUDGET)

            return _fallback

        client = genai.Client(api_key=settings.google_api_key)
        model = settings.llm_model

        system = (
            "You summarize long research conversations.\n"
            "Preserve:\n"
            "- Key conclusions with any citation identifiers mentioned\n"
            "- Unresolved contradictions\n"
            "- User preferences / constraints\n"
            f"Keep under ~{cls.SUMMARY_TOKEN_BUDGET} tokens.\n"
            "Be concise and structured."
        )

        async def _summarize(text: str) -> str:
            resp = await client.aio.models.generate_content(  # type: ignore[union-attr]
                model=model,
                contents=text,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    temperature=0.2,
                    max_output_tokens=cls.SUMMARY_TOKEN_BUDGET,
                ),
            )
            return (resp.text or "").strip()

        return _summarize


def _parse_session_id(raw: str) -> UUID:
    try:
        return UUID(str(raw))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid session_id",
        ) from exc


def _clip_to_token_budget(text: str, token_budget: int) -> str:
    if token_budget <= 0:
        return ""
    # Convert token budget to approximate character budget.
    char_budget = token_budget * 4
    t = (text or "").strip()
    if len(t) <= char_budget:
        return t
    return t[: max(0, char_budget - 3)].rstrip() + "..."
