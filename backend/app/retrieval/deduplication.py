"""Near-duplicate detection utilities (MinHash/LSH).

This module prefers the `datasketch` library for MinHash/LSH. If `datasketch`
is not installed, the deduplicator can still be imported, but constructing
`MinHashDeduplicator` will raise a clear error.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable

try:
    from datasketch import MinHash, MinHashLSH  # type: ignore
except Exception:  # pragma: no cover
    MinHash = None  # type: ignore[assignment]
    MinHashLSH = None  # type: ignore[assignment]


_WHITESPACE_RE = re.compile(r"\s+")
_NONWORD_RE = re.compile(r"[^\w\s]", flags=re.UNICODE)


def _normalize_text(text: str) -> str:
    text = text.lower().strip()
    text = _NONWORD_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub(" ", text)
    return text


def _char_3grams(text: str) -> list[str]:
    """Character 3-grams over normalized text.

    This is intentionally character-based (not word-based) to remain robust to
    small insertions/deletions that would otherwise shift most word n-grams.
    """
    normalized = _normalize_text(text)
    if not normalized:
        return []
    if len(normalized) <= 3:
        return [normalized]
    return [normalized[i : i + 3] for i in range(len(normalized) - 2)]


@dataclass(frozen=True)
class DedupItem:
    """A unit of text to deduplicate with provenance."""

    text: str
    source_name: str = ""
    item_id: str = ""


class MinHashDeduplicator:
    """Detect and remove near-duplicate items using MinHash + LSH.

    Configuration defaults follow the project blueprint:
    - 3-gram shingles (word-based)
    - 128 permutations
    - threshold 0.8 (approx Jaccard)
    """

    _AUTHORITY_ORDER: tuple[str, ...] = (
        "arxiv",
        "wikipedia",
        "hackernews",
        "reddit",
        "duckduckgo",
    )

    def __init__(self, *, num_perm: int = 128, threshold: float = 0.8) -> None:
        if MinHash is None or MinHashLSH is None:  # pragma: no cover
            raise RuntimeError("datasketch is not installed")
        if num_perm <= 0:
            raise ValueError("num_perm must be positive")
        if not (0.0 < threshold <= 1.0):
            raise ValueError("threshold must be in (0, 1]")
        self._num_perm = num_perm
        self._threshold = threshold

        self._authority_rank: dict[str, int] = {
            name: idx for idx, name in enumerate(self._AUTHORITY_ORDER)
        }
        self._default_rank = len(self._AUTHORITY_ORDER)

    @property
    def num_perm(self) -> int:
        return self._num_perm

    @property
    def threshold(self) -> float:
        return self._threshold

    def compute_signature(self, text: str) -> MinHash:
        if MinHash is None:  # pragma: no cover
            raise RuntimeError("datasketch is not installed")
        m = MinHash(num_perm=self._num_perm)
        for shingle in _char_3grams(text):
            m.update(shingle.encode("utf-8"))
        return m

    def find_duplicates(self, texts: list[str]) -> list[set[int]]:
        """Return connected groups of near-duplicate indices."""
        if not texts:
            return []

        signatures = [self.compute_signature(t) for t in texts]
        if MinHashLSH is None:  # pragma: no cover
            raise RuntimeError("datasketch is not installed")
        lsh = MinHashLSH(threshold=self._threshold, num_perm=self._num_perm)

        for i, sig in enumerate(signatures):
            lsh.insert(str(i), sig)

        parent = list(range(len(texts)))

        def find(x: int) -> int:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a: int, b: int) -> None:
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[rb] = ra

        for i, sig in enumerate(signatures):
            for key in lsh.query(sig):
                j = int(key)
                if j == i:
                    continue
                if sig.jaccard(signatures[j]) >= self._threshold:
                    union(i, j)

        groups: dict[int, set[int]] = {}
        for idx in range(len(texts)):
            root = find(idx)
            groups.setdefault(root, set()).add(idx)

        return [g for g in groups.values() if len(g) > 1]

    def deduplicate(self, items: list[DedupItem]) -> list[DedupItem]:
        """Deduplicate items, keeping the highest-authority representative."""
        if not items:
            return []

        texts = [i.text for i in items]
        dup_groups = self.find_duplicates(texts)
        if not dup_groups:
            return items

        index_to_group: dict[int, set[int]] = {}
        for g in dup_groups:
            for idx in g:
                index_to_group[idx] = g

        keep_indices: set[int] = set(range(len(items)))

        for g in dup_groups:
            winner = self._select_authoritative(items, g)
            for idx in g:
                if idx != winner:
                    keep_indices.discard(idx)

        return [items[i] for i in range(len(items)) if i in keep_indices]

    def _select_authoritative(
        self, items: list[DedupItem], group: Iterable[int]
    ) -> int:
        def score(idx: int) -> tuple[int, int, int]:
            item = items[idx]
            rank = self._authority_rank.get(item.source_name, self._default_rank)
            # Prefer higher authority (lower rank), then longer content, then earlier.
            return (rank, -len(item.text), idx)

        return min(group, key=score)
