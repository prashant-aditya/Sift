"""Recursive character text splitter with token-based sizing."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

import tiktoken
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class Chunk(BaseModel):
    """A text fragment with full provenance metadata and optional embedding."""

    chunk_id: str
    text: str
    source_url: str
    source_name: str
    source_title: str
    chunk_index: int
    total_chunks: int
    published_date: datetime | None = None
    fetched_at: datetime
    embedding: list[float] | None = None


class TextChunker:
    """Recursive character text splitter inspired by LangChain.

    Splits text using a hierarchy of separators (``\\n\\n`` -> ``\\n`` ->
    ``. `` -> `` ``), falling back to raw token-level splitting when no
    separator produces sub-chunk-size pieces.

    Token counting uses the *cl100k_base* encoding from ``tiktoken``.
    """

    SPLIT_HIERARCHY: list[str] = ["\n\n", "\n", ". ", " "]

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 64) -> None:
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._encoding = tiktoken.get_encoding("cl100k_base")

    def token_count(self, text: str) -> int:
        """Return the number of tokens in *text*."""
        return len(self._encoding.encode(text))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def chunk(
        self,
        text: str,
        *,
        source_url: str,
        source_name: str,
        source_title: str,
        published_date: datetime | None = None,
    ) -> list[Chunk]:
        """Split *text* into :class:`Chunk` objects with full metadata."""
        if not text or not text.strip():
            return []

        raw_pieces = self._split_text(text, list(self.SPLIT_HIERARCHY))
        if not raw_pieces:
            return []

        now = datetime.now(timezone.utc)
        total = len(raw_pieces)

        return [
            Chunk(
                chunk_id=str(uuid.uuid4()),
                text=piece,
                source_url=source_url,
                source_name=source_name,
                source_title=source_title,
                chunk_index=idx,
                total_chunks=total,
                published_date=published_date,
                fetched_at=now,
            )
            for idx, piece in enumerate(raw_pieces)
        ]

    # ------------------------------------------------------------------
    # Internal splitting
    # ------------------------------------------------------------------

    def _split_text(self, text: str, separators: list[str]) -> list[str]:
        """Recursively split *text* using the separator hierarchy."""
        if self.token_count(text) <= self._chunk_size:
            return [text.strip()] if text.strip() else []

        separator = ""
        remaining_separators: list[str] = []
        for i, sep in enumerate(separators):
            if sep in text:
                separator = sep
                remaining_separators = separators[i + 1 :]
                break

        if not separator:
            return self._split_by_tokens(text)

        parts = text.split(separator)

        good_splits: list[str] = []
        final_chunks: list[str] = []

        for part in parts:
            if self.token_count(part) <= self._chunk_size:
                good_splits.append(part)
            else:
                if good_splits:
                    merged = self._merge_splits(good_splits, separator)
                    final_chunks.extend(merged)
                    good_splits = []
                sub = self._split_text(part, remaining_separators)
                final_chunks.extend(sub)

        if good_splits:
            merged = self._merge_splits(good_splits, separator)
            final_chunks.extend(merged)

        return [c for c in final_chunks if c.strip()]

    def _merge_splits(self, splits: list[str], separator: str) -> list[str]:
        """Merge small splits back together respecting *chunk_size* and *overlap*."""
        chunks: list[str] = []
        current: list[str] = []
        current_tokens = 0
        sep_tokens = self.token_count(separator) if separator else 0

        for split in splits:
            split_tokens = self.token_count(split)
            added = split_tokens + (sep_tokens if current else 0)

            if current_tokens + added > self._chunk_size and current:
                chunk_text = separator.join(current).strip()
                if chunk_text:
                    chunks.append(chunk_text)

                # Retain trailing pieces for overlap
                while current_tokens > self._chunk_overlap and len(current) > 1:
                    dropped = self.token_count(current[0]) + sep_tokens
                    current_tokens -= dropped
                    current.pop(0)

            current.append(split)
            current_tokens += added

        if current:
            chunk_text = separator.join(current).strip()
            if chunk_text:
                chunks.append(chunk_text)

        return chunks

    def _split_by_tokens(self, text: str) -> list[str]:
        """Last-resort splitting at token boundaries."""
        tokens = self._encoding.encode(text)
        chunks: list[str] = []
        start = 0
        while start < len(tokens):
            end = min(start + self._chunk_size, len(tokens))
            chunk_text = self._encoding.decode(tokens[start:end]).strip()
            if chunk_text:
                chunks.append(chunk_text)
            if end >= len(tokens):
                break
            start = end - self._chunk_overlap
        return chunks
