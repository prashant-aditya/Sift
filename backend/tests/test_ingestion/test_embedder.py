"""Tests for EmbeddingGenerator: batching, retries, fallback behaviour."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.ingestion.embedder import BATCH_SIZE, DIMENSIONS, EmbeddingGenerator


@pytest.fixture
def mock_hf_response():
    """Factory for mock HF API responses (one 384-dim vector per input)."""

    def _build(n: int) -> list[list[float]]:
        return [[0.1] * DIMENSIONS for _ in range(n)]

    return _build


class TestBatching:
    @pytest.mark.asyncio
    async def test_single_batch(self, mock_hf_response):
        gen = EmbeddingGenerator(hf_api_token="test-token")
        texts = ["hello world"] * 5

        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_hf_response(5)

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
            result = await gen.embed(texts)

        assert len(result) == 5
        assert all(len(v) == DIMENSIONS for v in result)

    @pytest.mark.asyncio
    async def test_multiple_batches(self, mock_hf_response):
        gen = EmbeddingGenerator(hf_api_token="test-token")
        texts = ["text"] * (BATCH_SIZE + 10)

        call_count = 0

        async def _mock_post(url, json, headers):
            nonlocal call_count
            call_count += 1
            resp = MagicMock(spec=httpx.Response)
            resp.status_code = 200
            resp.json.return_value = mock_hf_response(len(json["inputs"]))
            return resp

        with patch("httpx.AsyncClient.post", side_effect=_mock_post):
            result = await gen.embed(texts)

        assert len(result) == BATCH_SIZE + 10
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_empty_input(self):
        gen = EmbeddingGenerator(hf_api_token="test-token")
        result = await gen.embed([])
        assert result == []


class TestRetries:
    @pytest.mark.asyncio
    async def test_retries_on_429(self, mock_hf_response):
        gen = EmbeddingGenerator(hf_api_token="test-token")

        call_count = 0

        async def _mock_post(url, json, headers):
            nonlocal call_count
            call_count += 1
            resp = MagicMock(spec=httpx.Response)
            if call_count < 3:
                resp.status_code = 429
                resp.raise_for_status = MagicMock(
                    side_effect=httpx.HTTPStatusError(
                        "rate limited", request=MagicMock(), response=resp
                    )
                )
            else:
                resp.status_code = 200
                resp.json.return_value = mock_hf_response(1)
            return resp

        with patch("httpx.AsyncClient.post", side_effect=_mock_post), \
             patch("asyncio.sleep", new_callable=AsyncMock):
            result = await gen.embed(["test"])

        assert call_count == 3
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_retries_on_503(self, mock_hf_response):
        gen = EmbeddingGenerator(hf_api_token="test-token")

        call_count = 0

        async def _mock_post(url, json, headers):
            nonlocal call_count
            call_count += 1
            resp = MagicMock(spec=httpx.Response)
            if call_count == 1:
                resp.status_code = 503
                resp.raise_for_status = MagicMock(
                    side_effect=httpx.HTTPStatusError(
                        "unavailable", request=MagicMock(), response=resp
                    )
                )
            else:
                resp.status_code = 200
                resp.json.return_value = mock_hf_response(1)
            return resp

        with patch("httpx.AsyncClient.post", side_effect=_mock_post), \
             patch("asyncio.sleep", new_callable=AsyncMock):
            result = await gen.embed(["test"])

        assert call_count == 2
        assert len(result) == 1


class TestFallback:
    @pytest.mark.asyncio
    async def test_falls_back_when_no_token(self):
        gen = EmbeddingGenerator(hf_api_token="")

        mock_model = MagicMock()
        mock_model.encode.return_value = [
            MagicMock(tolist=MagicMock(return_value=[0.5] * DIMENSIONS))
        ]
        gen._local_model = mock_model

        result = await gen.embed(["test"])
        assert len(result) == 1
        assert len(result[0]) == DIMENSIONS
        mock_model.encode.assert_called_once_with(["test"])

    @pytest.mark.asyncio
    async def test_falls_back_on_api_failure(self):
        gen = EmbeddingGenerator(hf_api_token="test-token")

        mock_model = MagicMock()
        mock_model.encode.return_value = [
            MagicMock(tolist=MagicMock(return_value=[0.5] * DIMENSIONS))
        ]
        gen._local_model = mock_model

        async def _failing_post(url, json, headers):
            raise httpx.ConnectError("connection refused")

        with patch("httpx.AsyncClient.post", side_effect=_failing_post):
            result = await gen.embed(["test"])

        assert len(result) == 1
        mock_model.encode.assert_called_once()


class TestNormalisation:
    @pytest.mark.asyncio
    async def test_token_level_embeddings_are_pooled(self):
        """HF API sometimes returns per-token embeddings; we mean-pool them."""
        gen = EmbeddingGenerator(hf_api_token="test-token")

        token_level = [[[1.0, 2.0, 3.0], [3.0, 4.0, 5.0]]]

        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = token_level

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
            result = await gen.embed(["test"])

        assert len(result) == 1
        assert result[0] == pytest.approx([2.0, 3.0, 4.0])
