"""Query decomposition engine using Google Gemini (GenAI) LLM.

Breaks complex research queries into 2-4 focused sub-queries that can be
independently searched across multiple sources.  Simple, already-focused
queries are returned as a single-element list.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Optional

import httpx
from google import genai
from google.genai import types

from app.config import get_settings
from app.core.prompts import DECOMPOSITION_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

DEFAULT_TEMPERATURE = 0.1
MAX_SUB_QUERIES = 4


class QueryAnalyzer:
    """Decomposes user queries into focused sub-queries via the Gemini API.

    Parameters
    ----------
    api_key:
        Google API key. Falls back to ``Settings.google_api_key``.
    model:
        Chat model identifier.  Falls back to ``Settings.llm_model``.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        settings = get_settings()
        self._provider = (settings.llm_provider or "google").lower()
        self._api_key = api_key or (
            settings.nvidia_api_key
            if self._provider == "nvidia"
            else settings.google_api_key
        )
        self._model = model or settings.llm_model
        self._nvidia_base_url = settings.nvidia_base_url.rstrip("/")

        # Use the async client surface for FastAPI usage.
        self._client = (
            genai.Client(api_key=self._api_key) if self._provider != "nvidia" else None
        )

    async def decompose(self, query: str) -> list[str]:
        """Break *query* into a list of focused sub-queries.

        Returns a single-element list when the query is already simple.
        Falls back to splitting on newlines if the LLM response is not
        valid JSON.
        """
        query = query.strip()
        if not query:
            return []

        if self._provider == "nvidia":
            raw = await self._decompose_via_nvidia(query)
        else:
            response = await self._client.aio.models.generate_content(  # type: ignore[union-attr]
                model=self._model,
                contents=query,
                config=types.GenerateContentConfig(
                    system_instruction=DECOMPOSITION_SYSTEM_PROMPT,
                    temperature=DEFAULT_TEMPERATURE,
                ),
            )
            raw = (response.text or "").strip()
        logger.debug("QueryAnalyzer raw response: %s", raw)

        sub_queries = self._parse_response(raw, original_query=query)
        return sub_queries[:MAX_SUB_QUERIES]

    async def _decompose_via_nvidia(self, query: str) -> str:
        url = f"{self._nvidia_base_url}/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self._api_key}"}
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": DECOMPOSITION_SYSTEM_PROMPT},
                {"role": "user", "content": query},
            ],
            "temperature": DEFAULT_TEMPERATURE,
            "stream": False,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return (
                ((data.get("choices") or [{}])[0].get("message") or {})
                .get("content", "")
                .strip()
            )

    @staticmethod
    def _parse_response(raw: str, *, original_query: str) -> list[str]:
        """Parse the LLM output into a list of query strings.

        Strategy:
        1. Try ``json.loads`` directly.
        2. Try extracting the first JSON array from the text (handles
           markdown fences or stray prose around the array).
        3. Fall back to splitting on newlines and stripping bullets /
           numbering prefixes.
        4. If nothing usable remains, return the original query.
        """
        parsed = _try_json_parse(raw)
        if parsed is not None:
            return parsed

        match = re.search(r"\[.*]", raw, re.DOTALL)
        if match:
            parsed = _try_json_parse(match.group(0))
            if parsed is not None:
                return parsed

        lines = [
            re.sub(r"^\s*[-*\d.)\]]+\s*", "", line).strip()
            for line in raw.splitlines()
            if line.strip()
        ]
        lines = [line for line in lines if line]
        if lines:
            return lines

        return [original_query]


def _try_json_parse(text: str) -> Optional[list[str]]:
    """Return a list of non-empty strings if *text* is a valid JSON array."""
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None

    if not isinstance(data, list):
        return None

    result = [str(item).strip() for item in data if str(item).strip()]
    return result if result else None
