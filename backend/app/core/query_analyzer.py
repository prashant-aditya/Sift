"""Query decomposition engine using Groq LLM.

Breaks complex research queries into 2-4 focused sub-queries that can be
independently searched across multiple sources.  Simple, already-focused
queries are returned as a single-element list.
"""

from __future__ import annotations

import json
import logging
import re

from groq import AsyncGroq

from app.config import get_settings

logger = logging.getLogger(__name__)

DECOMPOSITION_SYSTEM_PROMPT = """\
You are a research query decomposition engine.

Analyze the user's research query and decide whether it is:
1. **Simple** — a single, focused question that can be answered with one search.
2. **Complex** — a broad or multi-faceted question that benefits from being
   split into 2-4 independent, focused sub-queries.

Rules:
- If simple, return a JSON array containing only the original query.
- If complex, return a JSON array of 2-4 focused sub-queries.
- Each sub-query must be self-contained and independently searchable.
- Cover different facets of the original question (e.g. definitions,
  comparisons, trade-offs, practical use-cases).
- Do NOT repeat the same question in different wording.
- Return ONLY a valid JSON array of strings.  No explanation, no markdown
  fences, no extra text."""

DEFAULT_TEMPERATURE = 0.1
MAX_SUB_QUERIES = 4


class QueryAnalyzer:
    """Decomposes user queries into focused sub-queries via the Groq API.

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

    async def decompose(self, query: str) -> list[str]:
        """Break *query* into a list of focused sub-queries.

        Returns a single-element list when the query is already simple.
        Falls back to splitting on newlines if the LLM response is not
        valid JSON.
        """
        query = query.strip()
        if not query:
            return []

        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": DECOMPOSITION_SYSTEM_PROMPT},
                {"role": "user", "content": query},
            ],
            temperature=DEFAULT_TEMPERATURE,
        )

        raw = (response.choices[0].message.content or "").strip()
        logger.debug("QueryAnalyzer raw response: %s", raw)

        sub_queries = self._parse_response(raw, original_query=query)
        return sub_queries[:MAX_SUB_QUERIES]

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
        lines = [l for l in lines if l]
        if lines:
            return lines

        return [original_query]


def _try_json_parse(text: str) -> list[str] | None:
    """Return a list of non-empty strings if *text* is a valid JSON array."""
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None

    if not isinstance(data, list):
        return None

    result = [str(item).strip() for item in data if str(item).strip()]
    return result if result else None
