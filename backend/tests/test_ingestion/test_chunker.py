"""Tests for TextChunker: sizes, overlaps, metadata preservation."""

from datetime import datetime, timezone

from app.ingestion.chunker import TextChunker


def _make_chunker(**kwargs) -> TextChunker:
    defaults = {"chunk_size": 50, "chunk_overlap": 10}
    defaults.update(kwargs)
    return TextChunker(**defaults)


CHUNK_META = {
    "source_url": "https://example.com/article",
    "source_name": "test_source",
    "source_title": "Test Article",
    "published_date": datetime(2025, 1, 1, tzinfo=timezone.utc),
}


class TestChunkSizes:
    def test_short_text_single_chunk(self):
        chunker = _make_chunker(chunk_size=100)
        chunks = chunker.chunk("A short sentence.", **CHUNK_META)
        assert len(chunks) == 1
        assert chunks[0].text == "A short sentence."

    def test_text_splits_when_exceeding_size(self):
        chunker = _make_chunker(chunk_size=20, chunk_overlap=5)
        text = " ".join(["word"] * 100)
        chunks = chunker.chunk(text, **CHUNK_META)
        assert len(chunks) > 1
        for chunk in chunks:
            token_count = chunker.token_count(chunk.text)
            tolerance = int(20 * 1.15)
            assert token_count <= tolerance, (
                f"Chunk has {token_count} tokens, exceeds {tolerance}"
            )

    def test_empty_text_returns_no_chunks(self):
        chunker = _make_chunker()
        assert chunker.chunk("", **CHUNK_META) == []
        assert chunker.chunk("   ", **CHUNK_META) == []

    def test_respects_paragraph_separator(self):
        chunker = _make_chunker(chunk_size=30, chunk_overlap=5)
        text = "First paragraph content here.\n\nSecond paragraph content here."
        chunks = chunker.chunk(text, **CHUNK_META)
        assert len(chunks) >= 1
        full_text = " ".join(c.text for c in chunks)
        assert "First paragraph" in full_text
        assert "Second paragraph" in full_text

    def test_respects_sentence_separator(self):
        chunker = _make_chunker(chunk_size=20, chunk_overlap=5)
        sentences = [
            f"Sentence number {i} with extra words to fill up tokens."
            for i in range(10)
        ]
        text = " ".join(sentences)
        chunks = chunker.chunk(text, **CHUNK_META)
        assert len(chunks) >= 2


class TestChunkOverlap:
    def test_consecutive_chunks_share_content(self):
        chunker = _make_chunker(chunk_size=20, chunk_overlap=5)
        words = [f"word{i}" for i in range(80)]
        text = " ".join(words)
        chunks = chunker.chunk(text, **CHUNK_META)
        if len(chunks) >= 2:
            for i in range(1, len(chunks)):
                prev_words = set(chunks[i - 1].text.split())
                curr_words = set(chunks[i].text.split())
                overlap = prev_words & curr_words
                assert len(overlap) > 0, f"Chunks {i - 1} and {i} share no words"


class TestMetadataPreservation:
    def test_all_metadata_fields_set(self):
        chunker = _make_chunker(chunk_size=200)
        text = "Some content to chunk into a single piece."
        chunks = chunker.chunk(text, **CHUNK_META)
        assert len(chunks) == 1
        c = chunks[0]
        assert c.source_url == CHUNK_META["source_url"]
        assert c.source_name == CHUNK_META["source_name"]
        assert c.source_title == CHUNK_META["source_title"]
        assert c.published_date == CHUNK_META["published_date"]
        assert c.chunk_id  # non-empty UUID
        assert c.chunk_index == 0
        assert c.total_chunks == 1
        assert c.fetched_at is not None

    def test_chunk_indices_sequential(self):
        chunker = _make_chunker(chunk_size=15, chunk_overlap=3)
        text = " ".join(["content"] * 60)
        chunks = chunker.chunk(text, **CHUNK_META)
        assert len(chunks) > 1
        for i, c in enumerate(chunks):
            assert c.chunk_index == i
            assert c.total_chunks == len(chunks)

    def test_chunk_ids_unique(self):
        chunker = _make_chunker(chunk_size=15, chunk_overlap=3)
        text = " ".join(["data"] * 60)
        chunks = chunker.chunk(text, **CHUNK_META)
        ids = [c.chunk_id for c in chunks]
        assert len(ids) == len(set(ids)), "Chunk IDs must be unique"

    def test_published_date_none_allowed(self):
        chunker = _make_chunker(chunk_size=200)
        meta = {**CHUNK_META, "published_date": None}
        chunks = chunker.chunk("Some text.", **meta)
        assert chunks[0].published_date is None


class TestTokenCounting:
    def test_token_count_matches_tiktoken(self):
        import tiktoken

        enc = tiktoken.get_encoding("cl100k_base")
        chunker = _make_chunker()
        text = "The quick brown fox jumps over the lazy dog."
        assert chunker.token_count(text) == len(enc.encode(text))

    def test_token_count_empty(self):
        chunker = _make_chunker()
        assert chunker.token_count("") == 0
