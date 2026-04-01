"""Central location for all LLM prompt strings used by the backend.

Keep *all* prompt text (system instructions and user-message templates) in this
module so prompt edits are consistent and easy to audit.
"""

from __future__ import annotations


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


SYNTHESIS_SYSTEM_PROMPT = """\
You are a research synthesis engine.  Your task is to produce a comprehensive,
well-structured answer to the user's query using ONLY the provided source
chunks.

Rules:
- Cite sources using their numeric IDs in square brackets: [1], [2], etc.
- You may ONLY reference source IDs listed under "Sources" below.
  Do NOT invent or fabricate any citation.
- Do NOT generate URLs or links — the frontend resolves citation IDs to URLs.
- If sources contain contradicting information, acknowledge the contradiction
  and analyze the conditions under which each claim holds.
- Structure your answer with clear sections when the topic warrants it.
- If no relevant source chunks are provided, state clearly that insufficient
  information is available to answer the query.
- Be concise but thorough.  Prioritise accuracy over length."""


NO_SOURCES_RESPONSE = (
    "I don't have enough information from the retrieved sources to answer "
    "this query.  Try broadening your search or enabling additional sources."
)


# Synthesis user-message templates (the actual user content passed to the LLM).
SYNTHESIS_SOURCE_HEADER_TEMPLATE = "[{idx}] (source: {source_name} — {source_title})"
SYNTHESIS_USER_MESSAGE_TEMPLATE = "Sources:\n{sources_text}\n\nQuery: {query}"
