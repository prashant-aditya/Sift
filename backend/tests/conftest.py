import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from app.config import get_settings
from app.db.vector_store import VectorStore
from app.sources.base import SourceResult


@pytest.fixture(autouse=True)
def _reset_settings_cache():
    """Clear the lru_cache on get_settings between tests."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def mock_groq_client():
    """Mocked LLM client for QueryAnalyzer and Synthesizer tests.

    The project plan names this fixture ``mock_groq_client``; the codebase
    uses Google GenAI (Gemini), so this fixture mocks the ``genai.Client``
    async surface used by :class:`QueryAnalyzer` and :class:`Synthesizer`.
    """
    client = MagicMock()
    client.aio.models.generate_content = AsyncMock()
    client.aio.models.generate_content_stream = AsyncMock()
    return client


@pytest.fixture
def sample_source_results() -> list[SourceResult]:
    """Pre-built SourceResult objects for cross-module test reuse."""
    return [
        SourceResult(
            title="Python Programming",
            url="https://example.com/python",
            snippet="Python is a high-level programming language.",
            raw_content="Python is a high-level, interpreted programming language known for readability.",
            source_name="duckduckgo",
            published_date=datetime(2025, 1, 15, tzinfo=timezone.utc),
        ),
        SourceResult(
            title="FastAPI Framework",
            url="https://example.com/fastapi",
            snippet="FastAPI is a modern web framework for Python.",
            raw_content="<html><body><p>FastAPI is a modern, fast web framework for building APIs.</p></body></html>",
            source_name="wikipedia",
            published_date=datetime(2025, 3, 1, tzinfo=timezone.utc),
        ),
        SourceResult(
            title="Machine Learning Discussion",
            url="https://news.ycombinator.com/item?id=12345",
            snippet="200 points | 45 comments",
            raw_content="ML is transforming how software is built and deployed.",
            source_name="hackernews",
            metadata={"points": 200, "num_comments": 45},
        ),
    ]


@pytest.fixture
def temp_chroma_dir(tmp_path) -> str:
    """Temporary directory for ChromaDB persistence during tests."""
    return str(tmp_path / "test_chroma")


@pytest.fixture
def vector_store(temp_chroma_dir) -> VectorStore:
    """VectorStore backed by a pytest-managed temporary directory."""
    return VectorStore(persist_dir=temp_chroma_dir)
