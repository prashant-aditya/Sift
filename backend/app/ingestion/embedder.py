"""Embedding generation via HuggingFace Inference API with local fallback."""

from __future__ import annotations

import asyncio
import logging

import httpx
import numpy as np

logger = logging.getLogger(__name__)

_HF_FEATURE_EXTRACTION_URL = (
    "https://api-inference.huggingface.co/pipeline/feature-extraction/"
    "sentence-transformers/{model}"
)

BATCH_SIZE = 32
MAX_RETRIES = 2
BACKOFF_BASE_SECONDS = 1.0
DIMENSIONS = 384


class EmbeddingGenerator:
    """Generate 384-dim embeddings using HuggingFace API (primary) or
    a local ``sentence-transformers`` model (fallback).

    Parameters
    ----------
    hf_api_token:
        Bearer token for the HuggingFace Inference API.  When empty, the
        generator falls back to the local model immediately.
    model_name:
        Name of the sentence-transformers model used for both remote and
        local inference.
    """

    def __init__(
        self,
        hf_api_token: str = "",
        model_name: str = "all-MiniLM-L6-v2",
    ) -> None:
        self._hf_api_token = hf_api_token
        self._model_name = model_name
        self._api_url = _HF_FEATURE_EXTRACTION_URL.format(model=model_name)
        self._local_model: object | None = None  # lazy-loaded SentenceTransformer

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Return a list of 384-dim embeddings, one per input text."""
        if not texts:
            return []

        all_embeddings: list[list[float]] = []
        for start in range(0, len(texts), BATCH_SIZE):
            batch = texts[start : start + BATCH_SIZE]
            embeddings = await self._embed_batch(batch)
            all_embeddings.extend(embeddings)
        return all_embeddings

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        if self._hf_api_token:
            try:
                return await self._embed_via_api(texts)
            except Exception as exc:
                logger.warning(
                    "HF Inference API failed (%s); falling back to local model",
                    exc,
                )
        return self._embed_locally(texts)

    async def _embed_via_api(self, texts: list[str]) -> list[list[float]]:
        headers = {"Authorization": f"Bearer {self._hf_api_token}"}
        payload = {"inputs": texts, "options": {"wait_for_model": True}}

        for attempt in range(MAX_RETRIES + 1):
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self._api_url, json=payload, headers=headers
                )

            if response.status_code == 200:
                raw = response.json()
                return [_normalise_embedding(e) for e in raw]

            if response.status_code in {429, 503} and attempt < MAX_RETRIES:
                delay = BACKOFF_BASE_SECONDS * (2**attempt)
                logger.info(
                    "HF API returned %d; retrying in %.1fs (attempt %d/%d)",
                    response.status_code,
                    delay,
                    attempt + 1,
                    MAX_RETRIES,
                )
                await asyncio.sleep(delay)
                continue

            response.raise_for_status()

        raise RuntimeError("HF Inference API embedding failed after all retries")

    def _embed_locally(self, texts: list[str]) -> list[list[float]]:
        if self._local_model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise RuntimeError(
                    "sentence-transformers is not installed and HF API is "
                    "unavailable.  Install it with: pip install sentence-transformers"
                ) from exc
            self._local_model = SentenceTransformer(self._model_name)

        embeddings = self._local_model.encode(texts)  # type: ignore[union-attr]
        return [e.tolist() for e in embeddings]


def _normalise_embedding(raw: list) -> list[float]:
    """Handle both sentence-level and token-level HF API responses.

    The feature-extraction pipeline may return token-level embeddings
    (a list of lists) instead of a single vector; in that case we
    mean-pool across the token dimension.
    """
    if not raw:
        return [0.0] * DIMENSIONS

    if isinstance(raw[0], list):
        return np.mean(raw, axis=0).tolist()

    return [float(v) for v in raw]
