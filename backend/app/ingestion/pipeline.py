"""Document ingestion pipeline: extract -> chunk -> embed."""

from __future__ import annotations

import logging
from typing import Optional

from app.ingestion.chunker import Chunk, TextChunker
from app.ingestion.embedder import EmbeddingGenerator
from app.ingestion.extractors import ContentExtractor
from app.sources.base import SourceResult

logger = logging.getLogger(__name__)


class IngestionPipeline:
    """Orchestrates the full ingestion flow.

    ``process(list[SourceResult])`` converts raw source results into a
    flat list of :class:`Chunk` objects, each carrying its embedding.

    Steps:
      1. Extract clean text from every :class:`SourceResult`
      2. Split each document into token-bounded chunks
      3. Generate embeddings for all chunks in batches
    """

    def __init__(
        self,
        extractor: Optional[ContentExtractor] = None,
        chunker: Optional[TextChunker] = None,
        embedder: Optional[EmbeddingGenerator] = None,
    ) -> None:
        self._extractor = extractor or ContentExtractor()
        self._chunker = chunker or TextChunker()
        self._embedder = embedder or EmbeddingGenerator()

    async def process(self, source_results: list[SourceResult]) -> list[Chunk]:
        """Run the full extract -> chunk -> embed pipeline."""
        if not source_results:
            return []

        all_chunks: list[Chunk] = []
        for result in source_results:
            text = self._extract_content(result)
            if not text:
                logger.debug("No extractable content from %s", result.url)
                continue

            chunks = self._chunker.chunk(
                text,
                source_url=result.url,
                source_name=result.source_name,
                source_title=result.title,
                published_date=result.published_date,
            )
            all_chunks.extend(chunks)

        if not all_chunks:
            logger.info("No chunks produced from %d source results", len(source_results))
            return []

        logger.info(
            "Embedding %d chunks from %d source results",
            len(all_chunks),
            len(source_results),
        )
        texts = [c.text for c in all_chunks]
        embeddings = await self._embedder.embed(texts)

        for chunk, emb in zip(all_chunks, embeddings):
            chunk.embedding = emb

        return all_chunks

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _extract_content(self, result: SourceResult) -> str:
        """Pick the best extraction strategy for a given source result."""
        if result.raw_content:
            if self._looks_like_html(result.raw_content):
                return self._extractor.extract_from_html(result.raw_content)
            return self._extractor.extract_from_text(result.raw_content)

        return self._extractor.extract_from_snippet(result.snippet, result.url)

    @staticmethod
    def _looks_like_html(text: str) -> bool:
        """Heuristic check for HTML content."""
        stripped = text.strip()[:500]
        return "<" in stripped and ">" in stripped
