"""BM25 (Okapi BM25) sparse retrieval index — implemented from scratch.

No external BM25 library is used.  The index stores an inverted posting list,
per-document token counts, and corpus-level statistics needed for IDF
computation.  It supports incremental document addition and pickle-based
persistence.
"""

from __future__ import annotations

import logging
import math
import pickle
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Sequence

logger = logging.getLogger(__name__)

# ── Stop-word list (hardcoded English) ──────────────────────────────────────

ENGLISH_STOP_WORDS: frozenset[str] = frozenset(
    {
        "a", "about", "above", "after", "again", "against", "all", "am", "an",
        "and", "any", "are", "aren't", "as", "at", "be", "because", "been",
        "before", "being", "below", "between", "both", "but", "by", "can",
        "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does",
        "doesn't", "doing", "don't", "down", "during", "each", "few", "for",
        "from", "further", "get", "got", "had", "hadn't", "has", "hasn't",
        "have", "haven't", "having", "he", "her", "here", "hers", "herself",
        "him", "himself", "his", "how", "i", "if", "in", "into", "is",
        "isn't", "it", "it's", "its", "itself", "just", "let's", "me",
        "might", "more", "most", "mustn't", "my", "myself", "no", "nor",
        "not", "of", "off", "on", "once", "only", "or", "other", "ought",
        "our", "ours", "ourselves", "out", "over", "own", "same", "shan't",
        "she", "should", "shouldn't", "so", "some", "such", "than", "that",
        "the", "their", "theirs", "them", "themselves", "then", "there",
        "these", "they", "this", "those", "through", "to", "too", "under",
        "until", "up", "very", "was", "wasn't", "we", "were", "weren't",
        "what", "when", "where", "which", "while", "who", "whom", "why",
        "will", "with", "won't", "would", "wouldn't", "you", "your", "yours",
        "yourself", "yourselves",
    }
)

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    """Lowercase, split on non-alphanumeric chars, and remove stop words."""
    return [tok for tok in _TOKEN_RE.findall(text.lower()) if tok not in ENGLISH_STOP_WORDS]


# ── Result type ─────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class BM25Result:
    """A single scored result from a BM25 query."""

    doc_index: int
    score: float
    document: str


# ── BM25 Index ──────────────────────────────────────────────────────────────


@dataclass
class BM25Index:
    """Okapi BM25 sparse retrieval index built from scratch.

    Parameters
    ----------
    k1:
        Term-frequency saturation parameter.  Higher values give more weight
        to repeated terms.
    b:
        Document-length normalisation factor.  ``0`` disables length
        normalisation; ``1`` fully normalises relative to average length.
    """

    k1: float = 1.5
    b: float = 0.75

    # Corpus state (populated by fit / add_documents)
    _documents: list[str] = field(default_factory=list, repr=False)
    _doc_lengths: list[int] = field(default_factory=list, repr=False)
    _avg_doc_length: float = field(default=0.0, repr=False)
    _n_docs: int = field(default=0, repr=False)

    # term → list[(doc_index, term_frequency)]
    _inverted_index: dict[str, list[tuple[int, int]]] = field(
        default_factory=dict, repr=False
    )
    # term → number of documents containing the term
    _doc_freqs: dict[str, int] = field(default_factory=dict, repr=False)

    # ── Tokenisation (CP-2.1.4) ────────────────────────────────────────

    @staticmethod
    def tokenize(text: str) -> list[str]:
        """Tokenize *text*: lowercase + split on non-alphanum + stop-word removal."""
        return tokenize(text)

    # ── fit (CP-2.1.2) ─────────────────────────────────────────────────

    def fit(self, documents: Sequence[str]) -> BM25Index:
        """Build the inverted index from *documents* (replaces any prior state).

        Returns ``self`` so callers can chain: ``idx = BM25Index().fit(docs)``.
        """
        self._documents = list(documents)
        self._n_docs = len(self._documents)
        self._inverted_index = {}
        self._doc_freqs = {}
        self._doc_lengths = []

        for doc_idx, doc in enumerate(self._documents):
            tokens = self.tokenize(doc)
            self._doc_lengths.append(len(tokens))
            tf_counter = Counter(tokens)

            for term, freq in tf_counter.items():
                self._inverted_index.setdefault(term, []).append((doc_idx, freq))
                self._doc_freqs[term] = self._doc_freqs.get(term, 0) + 1

        self._avg_doc_length = (
            sum(self._doc_lengths) / self._n_docs if self._n_docs else 0.0
        )

        logger.info(
            "BM25 index fitted — docs=%d, unique_terms=%d, avg_dl=%.1f",
            self._n_docs,
            len(self._inverted_index),
            self._avg_doc_length,
        )
        return self

    # ── query (CP-2.1.3) ───────────────────────────────────────────────

    def _idf(self, term: str) -> float:
        """IDF for *term*: ``log((N - df + 0.5) / (df + 0.5) + 1)``."""
        df = self._doc_freqs.get(term, 0)
        return math.log((self._n_docs - df + 0.5) / (df + 0.5) + 1.0)

    def query(self, query_text: str, top_k: int = 10) -> list[BM25Result]:
        """Score every document against *query_text* and return *top_k* results.

        Returns an empty list when the corpus is empty or when the query
        produces no matching tokens.
        """
        if self._n_docs == 0:
            return []

        query_tokens = self.tokenize(query_text)
        if not query_tokens:
            return []

        scores: dict[int, float] = {}

        for token in query_tokens:
            if token not in self._inverted_index:
                continue

            idf = self._idf(token)

            for doc_idx, tf in self._inverted_index[token]:
                dl = self._doc_lengths[doc_idx]
                numerator = tf * (self.k1 + 1.0)
                denominator = tf + self.k1 * (
                    1.0 - self.b + self.b * dl / self._avg_doc_length
                )
                scores[doc_idx] = scores.get(doc_idx, 0.0) + idf * numerator / denominator

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

        return [
            BM25Result(doc_index=doc_idx, score=score, document=self._documents[doc_idx])
            for doc_idx, score in ranked
        ]

    # ── add_documents (CP-2.1.5) ───────────────────────────────────────

    def add_documents(self, documents: Sequence[str]) -> None:
        """Incrementally add *documents* without rebuilding the full index.

        The inverted index, document frequencies, and corpus statistics are
        updated in-place so that subsequent queries reflect the new documents.
        """
        if not documents:
            return

        start_idx = self._n_docs

        for offset, doc in enumerate(documents):
            doc_idx = start_idx + offset
            self._documents.append(doc)
            tokens = self.tokenize(doc)
            self._doc_lengths.append(len(tokens))
            tf_counter = Counter(tokens)

            for term, freq in tf_counter.items():
                self._inverted_index.setdefault(term, []).append((doc_idx, freq))
                self._doc_freqs[term] = self._doc_freqs.get(term, 0) + 1

        self._n_docs = len(self._documents)
        self._avg_doc_length = (
            sum(self._doc_lengths) / self._n_docs if self._n_docs else 0.0
        )

        logger.info(
            "BM25 index updated — added=%d, total_docs=%d, avg_dl=%.1f",
            len(documents),
            self._n_docs,
            self._avg_doc_length,
        )

    # ── Persistence (CP-2.1.6) ─────────────────────────────────────────

    def save(self, path: str | Path) -> None:
        """Persist the fitted index to *path* using :mod:`pickle`."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        state = {
            "k1": self.k1,
            "b": self.b,
            "documents": self._documents,
            "doc_lengths": self._doc_lengths,
            "avg_doc_length": self._avg_doc_length,
            "n_docs": self._n_docs,
            "inverted_index": self._inverted_index,
            "doc_freqs": self._doc_freqs,
        }

        with open(path, "wb") as fh:
            pickle.dump(state, fh, protocol=pickle.HIGHEST_PROTOCOL)

        logger.info("BM25 index saved to %s (%d docs)", path, self._n_docs)

    @classmethod
    def load(cls, path: str | Path) -> BM25Index:
        """Load a previously saved index from *path*.

        Raises
        ------
        FileNotFoundError
            If *path* does not exist.
        """
        path = Path(path)

        with open(path, "rb") as fh:
            state: dict = pickle.load(fh)  # noqa: S301

        idx = cls(k1=state["k1"], b=state["b"])
        idx._documents = state["documents"]
        idx._doc_lengths = state["doc_lengths"]
        idx._avg_doc_length = state["avg_doc_length"]
        idx._n_docs = state["n_docs"]
        idx._inverted_index = state["inverted_index"]
        idx._doc_freqs = state["doc_freqs"]

        logger.info("BM25 index loaded from %s (%d docs)", path, idx._n_docs)
        return idx

    # ── Introspection helpers ──────────────────────────────────────────

    @property
    def n_docs(self) -> int:
        """Number of documents currently in the index."""
        return self._n_docs

    @property
    def vocabulary_size(self) -> int:
        """Number of unique terms in the index."""
        return len(self._inverted_index)

    def get_document(self, index: int) -> Optional[str]:
        """Return the document at *index*, or *None* if out of range."""
        if 0 <= index < self._n_docs:
            return self._documents[index]
        return None
