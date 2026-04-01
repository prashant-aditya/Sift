"""Tests for app.core.query_analyzer — query decomposition via Gemini."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.query_analyzer import QueryAnalyzer, _try_json_parse


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_gemini_response(text: str) -> MagicMock:
    response = MagicMock()
    response.text = text
    return response


# ---------------------------------------------------------------------------
# _try_json_parse unit tests
# ---------------------------------------------------------------------------


class TestTryJsonParse:
    def test_valid_array(self):
        assert _try_json_parse('["a", "b"]') == ["a", "b"]

    def test_single_element(self):
        assert _try_json_parse('["hello"]') == ["hello"]

    def test_not_an_array(self):
        assert _try_json_parse('{"key": "value"}') is None

    def test_empty_array(self):
        assert _try_json_parse("[]") is None

    def test_array_with_empty_strings(self):
        assert _try_json_parse('["", "  "]') is None

    def test_invalid_json(self):
        assert _try_json_parse("not json at all") is None

    def test_numeric_items_cast_to_str(self):
        result = _try_json_parse("[1, 2, 3]")
        assert result == ["1", "2", "3"]


# ---------------------------------------------------------------------------
# QueryAnalyzer.decompose tests (Groq API mocked)
# ---------------------------------------------------------------------------


class TestQueryAnalyzerDecompose:
    @pytest.fixture()
    def analyzer(self):
        with patch.dict("os.environ", {"GOOGLE_API_KEY": "test-key"}):
            return QueryAnalyzer(api_key="test-key")

    @pytest.mark.asyncio
    async def test_complex_query_returns_json_array(self, analyzer: QueryAnalyzer):
        """LLM returns a valid JSON array — should be parsed correctly."""
        mock_content = (
            '["What is Kafka?", "What is RabbitMQ?", "Kafka vs RabbitMQ trade-offs"]'
        )
        mock_resp = _mock_gemini_response(mock_content)

        analyzer._client.aio.models.generate_content = AsyncMock(return_value=mock_resp)

        result = await analyzer.decompose("Compare Kafka and RabbitMQ")

        assert isinstance(result, list)
        assert len(result) == 3
        assert "Kafka" in result[0]
        assert "RabbitMQ" in result[1]

    @pytest.mark.asyncio
    async def test_simple_query_passthrough(self, analyzer: QueryAnalyzer):
        """A simple query should be returned as a single-element array."""
        mock_content = '["What is Python?"]'
        mock_resp = _mock_gemini_response(mock_content)

        analyzer._client.aio.models.generate_content = AsyncMock(return_value=mock_resp)

        result = await analyzer.decompose("What is Python?")

        assert result == ["What is Python?"]

    @pytest.mark.asyncio
    async def test_json_with_markdown_fences(self, analyzer: QueryAnalyzer):
        """LLM wraps JSON in markdown code fences — should still parse."""
        mock_content = '```json\n["sub query 1", "sub query 2"]\n```'
        mock_resp = _mock_gemini_response(mock_content)

        analyzer._client.aio.models.generate_content = AsyncMock(return_value=mock_resp)

        result = await analyzer.decompose("complex question")

        assert result == ["sub query 1", "sub query 2"]

    @pytest.mark.asyncio
    async def test_fallback_to_newline_split(self, analyzer: QueryAnalyzer):
        """If the LLM returns plain text lines instead of JSON, fall back."""
        mock_content = (
            "1. What is Docker?\n2. How does Kubernetes work?\n3. Docker vs Kubernetes"
        )
        mock_resp = _mock_gemini_response(mock_content)

        analyzer._client.aio.models.generate_content = AsyncMock(return_value=mock_resp)

        result = await analyzer.decompose("Docker and Kubernetes")

        assert len(result) == 3
        assert "Docker" in result[0]
        assert "Kubernetes" in result[1]

    @pytest.mark.asyncio
    async def test_fallback_bullet_list(self, analyzer: QueryAnalyzer):
        """Bullet-prefixed lines should be cleaned and returned."""
        mock_content = "- What is React?\n- What is Vue?\n- React vs Vue"
        mock_resp = _mock_gemini_response(mock_content)

        analyzer._client.aio.models.generate_content = AsyncMock(return_value=mock_resp)

        result = await analyzer.decompose("React vs Vue")

        assert len(result) == 3
        assert "React" in result[0]

    @pytest.mark.asyncio
    async def test_empty_query_returns_empty(self, analyzer: QueryAnalyzer):
        result = await analyzer.decompose("")
        assert result == []

    @pytest.mark.asyncio
    async def test_whitespace_only_query_returns_empty(self, analyzer: QueryAnalyzer):
        result = await analyzer.decompose("   \n  ")
        assert result == []

    @pytest.mark.asyncio
    async def test_max_four_subqueries(self, analyzer: QueryAnalyzer):
        """Even if the LLM returns more than 4, we cap at MAX_SUB_QUERIES."""
        mock_content = '["q1", "q2", "q3", "q4", "q5", "q6"]'
        mock_resp = _mock_gemini_response(mock_content)

        analyzer._client.aio.models.generate_content = AsyncMock(return_value=mock_resp)

        result = await analyzer.decompose("big question")

        assert len(result) == 4

    @pytest.mark.asyncio
    async def test_totally_unparseable_falls_back_to_original(
        self, analyzer: QueryAnalyzer
    ):
        """If LLM returns gibberish with no usable lines, return original."""
        mock_content = ""
        mock_resp = _mock_gemini_response(mock_content)

        analyzer._client.aio.models.generate_content = AsyncMock(return_value=mock_resp)

        result = await analyzer.decompose("my original query")

        assert result == ["my original query"]

    @pytest.mark.asyncio
    async def test_gemini_api_called_with_correct_params(self, analyzer: QueryAnalyzer):
        mock_resp = _mock_gemini_response('["test"]')
        mock_generate = AsyncMock(return_value=mock_resp)
        analyzer._client.aio.models.generate_content = mock_generate

        await analyzer.decompose("test query")

        mock_generate.assert_called_once()
        call_kwargs = mock_generate.call_args.kwargs
        assert call_kwargs["model"] == analyzer._model
        assert call_kwargs["contents"] == "test query"
        assert call_kwargs["config"].temperature == 0.1
        assert call_kwargs["config"].system_instruction is not None
