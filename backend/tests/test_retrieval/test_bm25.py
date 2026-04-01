"""Tests for the BM25 sparse retrieval index (Goal 2.1)."""

from __future__ import annotations

import math

import pytest

from app.retrieval.bm25 import (
    BM25Index,
    BM25Result,
    ENGLISH_STOP_WORDS,
    tokenize,
)


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def sample_corpus() -> list[str]:
    """Small but varied corpus for most tests."""
    return [
        "Python is a high-level programming language known for readability",
        "Java is a statically typed programming language used in enterprise",
        "Rust provides memory safety without garbage collection",
        "Python and Rust are both popular for systems programming",
        "Machine learning with Python is growing rapidly",
    ]


@pytest.fixture
def fitted_index(sample_corpus: list[str]) -> BM25Index:
    """A BM25Index already fitted on the sample corpus."""
    return BM25Index().fit(sample_corpus)


# ── Tokenizer tests (CP-2.1.4) ─────────────────────────────────────────────


class TestTokenizer:
    def test_lowercasing(self) -> None:
        assert tokenize("Python JAVA Rust") == ["python", "java", "rust"]

    def test_stop_word_removal(self) -> None:
        tokens = tokenize("the quick brown fox is a very fast animal")
        assert "the" not in tokens
        assert "is" not in tokens
        assert "a" not in tokens
        assert "very" not in tokens
        assert "quick" in tokens
        assert "brown" in tokens
        assert "fox" in tokens

    def test_non_alpha_stripped(self) -> None:
        tokens = tokenize("hello-world! foo_bar (baz) 123")
        assert tokens == ["hello", "world", "foo", "bar", "baz", "123"]

    def test_empty_string(self) -> None:
        assert tokenize("") == []

    def test_only_stop_words(self) -> None:
        assert tokenize("the and is of to in a") == []

    def test_stop_words_set_contains_common_words(self) -> None:
        for word in ("the", "is", "at", "which", "on", "a", "an", "and", "or"):
            assert word in ENGLISH_STOP_WORDS


# ── fit() tests (CP-2.1.2) ─────────────────────────────────────────────────


class TestFit:
    def test_builds_inverted_index(self, fitted_index: BM25Index) -> None:
        assert fitted_index.n_docs == 5
        assert fitted_index.vocabulary_size > 0

    def test_doc_lengths_populated(self, fitted_index: BM25Index) -> None:
        assert len(fitted_index._doc_lengths) == 5
        assert all(dl > 0 for dl in fitted_index._doc_lengths)

    def test_avg_doc_length_positive(self, fitted_index: BM25Index) -> None:
        expected_avg = sum(fitted_index._doc_lengths) / 5
        assert fitted_index._avg_doc_length == pytest.approx(expected_avg)

    def test_inverted_index_entries(self, fitted_index: BM25Index) -> None:
        assert "python" in fitted_index._inverted_index
        postings = fitted_index._inverted_index["python"]
        doc_indices = {doc_idx for doc_idx, _ in postings}
        assert 0 in doc_indices  # doc 0 mentions Python
        assert 3 in doc_indices  # doc 3 mentions Python
        assert 4 in doc_indices  # doc 4 mentions Python

    def test_doc_freqs(self, fitted_index: BM25Index) -> None:
        assert fitted_index._doc_freqs["python"] == 3  # appears in docs 0, 3, 4
        assert fitted_index._doc_freqs["rust"] == 2  # appears in docs 2, 3

    def test_fit_replaces_prior_state(self, fitted_index: BM25Index) -> None:
        fitted_index.fit(["single document"])
        assert fitted_index.n_docs == 1
        assert fitted_index.vocabulary_size > 0

    def test_fit_returns_self(self, sample_corpus: list[str]) -> None:
        idx = BM25Index()
        result = idx.fit(sample_corpus)
        assert result is idx

    def test_empty_corpus(self) -> None:
        idx = BM25Index().fit([])
        assert idx.n_docs == 0
        assert idx._avg_doc_length == 0.0


# ── query() tests (CP-2.1.3) ───────────────────────────────────────────────


class TestQuery:
    def test_keyword_match_ranking(self, fitted_index: BM25Index) -> None:
        """Documents containing query terms should be ranked higher."""
        results = fitted_index.query("Python programming")
        assert len(results) > 0
        top_doc = results[0]
        assert (
            "python" in top_doc.document.lower()
            or "programming" in top_doc.document.lower()
        )

    def test_exact_keyword_top_ranked(self, fitted_index: BM25Index) -> None:
        """A query for 'Rust memory safety' should rank doc 2 highest."""
        results = fitted_index.query("Rust memory safety")
        assert results[0].doc_index == 2

    def test_returns_bm25_result_type(self, fitted_index: BM25Index) -> None:
        results = fitted_index.query("Python")
        assert all(isinstance(r, BM25Result) for r in results)

    def test_scores_are_positive(self, fitted_index: BM25Index) -> None:
        results = fitted_index.query("programming language")
        assert all(r.score > 0 for r in results)

    def test_scores_descending(self, fitted_index: BM25Index) -> None:
        results = fitted_index.query("Python programming")
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_top_k_limits_results(self, fitted_index: BM25Index) -> None:
        results = fitted_index.query("programming", top_k=2)
        assert len(results) <= 2

    def test_empty_query(self, fitted_index: BM25Index) -> None:
        results = fitted_index.query("")
        assert results == []

    def test_stop_words_only_query(self, fitted_index: BM25Index) -> None:
        results = fitted_index.query("the and is a")
        assert results == []

    def test_query_no_matching_terms(self, fitted_index: BM25Index) -> None:
        results = fitted_index.query("xylophone quasar nebula")
        assert results == []

    def test_query_empty_corpus(self) -> None:
        idx = BM25Index().fit([])
        results = idx.query("anything")
        assert results == []

    def test_single_doc_corpus(self) -> None:
        idx = BM25Index().fit(["Python is great for data science"])
        results = idx.query("Python data science")
        assert len(results) == 1
        assert results[0].doc_index == 0
        assert results[0].score > 0

    def test_document_text_in_result(self, fitted_index: BM25Index) -> None:
        results = fitted_index.query("machine learning")
        matching = [r for r in results if "Machine learning" in r.document]
        assert len(matching) >= 1

    def test_idf_discriminates_rare_terms(self) -> None:
        """A term appearing in fewer documents should have higher IDF."""
        docs = [
            "cat dog bird",
            "cat dog fish",
            "cat hamster snake",
            "cat lizard parrot",
        ]
        idx = BM25Index().fit(docs)
        idf_cat = idx._idf("cat")  # df=4 (all docs)
        idf_bird = idx._idf("bird")  # df=1
        assert idf_bird > idf_cat

    def test_bm25_score_manual_verification(self) -> None:
        """Verify BM25 score against hand-computed values for a tiny corpus."""
        docs = ["alpha beta gamma", "alpha alpha delta"]
        idx = BM25Index(k1=1.5, b=0.75).fit(docs)

        # "alpha" appears in both docs → df=2, N=2
        # IDF("alpha") = log((2 - 2 + 0.5) / (2 + 0.5) + 1) = log(0.5/2.5 + 1) = log(1.2)
        expected_idf_alpha = math.log(1.2)

        # doc 0: tokens = ["alpha", "beta", "gamma"], dl=3, tf_alpha=1
        # doc 1: tokens = ["alpha", "alpha", "delta"], dl=3, tf_alpha=2
        # avgdl = 3.0
        # doc 0 score for "alpha":
        #   IDF * (1 * 2.5) / (1 + 1.5*(1 - 0.75 + 0.75*3/3)) = IDF * 2.5 / 2.5 = IDF
        # doc 1 score for "alpha":
        #   IDF * (2 * 2.5) / (2 + 1.5*(1 - 0.75 + 0.75*3/3)) = IDF * 5.0 / 3.5

        results = idx.query("alpha", top_k=2)
        assert len(results) == 2
        assert results[0].doc_index == 1  # doc 1 has higher tf for "alpha"
        assert results[0].score == pytest.approx(expected_idf_alpha * 5.0 / 3.5)
        assert results[1].score == pytest.approx(expected_idf_alpha * 2.5 / 2.5)

    def test_multi_term_query_aggregation(self) -> None:
        """Score should be the sum of per-term BM25 contributions."""
        docs = ["cat dog", "cat fish", "dog bird"]
        idx = BM25Index(k1=1.5, b=0.75).fit(docs)

        results_cat = {r.doc_index: r.score for r in idx.query("cat", top_k=3)}
        results_dog = {r.doc_index: r.score for r in idx.query("dog", top_k=3)}
        results_both = {r.doc_index: r.score for r in idx.query("cat dog", top_k=3)}

        for doc_idx in results_both:
            expected = results_cat.get(doc_idx, 0.0) + results_dog.get(doc_idx, 0.0)
            assert results_both[doc_idx] == pytest.approx(expected)


# ── add_documents() tests (CP-2.1.5) ───────────────────────────────────────


class TestAddDocuments:
    def test_incremental_adds_docs(self, fitted_index: BM25Index) -> None:
        original_count = fitted_index.n_docs
        fitted_index.add_documents(["A brand new document about databases"])
        assert fitted_index.n_docs == original_count + 1

    def test_new_docs_are_queryable(self, fitted_index: BM25Index) -> None:
        fitted_index.add_documents(["Kubernetes orchestrates containerised workloads"])
        results = fitted_index.query("Kubernetes containers")
        assert len(results) > 0
        assert any("Kubernetes" in r.document for r in results)

    def test_new_doc_ranked_first_for_unique_term(
        self, fitted_index: BM25Index
    ) -> None:
        fitted_index.add_documents(["Quantum computing leverages superposition"])
        results = fitted_index.query("quantum superposition")
        assert results[0].document == "Quantum computing leverages superposition"

    def test_avg_doc_length_updated(self, fitted_index: BM25Index) -> None:
        old_avg = fitted_index._avg_doc_length
        fitted_index.add_documents(["short"])
        assert fitted_index._avg_doc_length != old_avg

    def test_doc_freqs_updated(self, fitted_index: BM25Index) -> None:
        old_python_df = fitted_index._doc_freqs.get("python", 0)
        fitted_index.add_documents(["Python scripting automation"])
        assert fitted_index._doc_freqs["python"] == old_python_df + 1

    def test_empty_add_is_noop(self, fitted_index: BM25Index) -> None:
        original = fitted_index.n_docs
        fitted_index.add_documents([])
        assert fitted_index.n_docs == original

    def test_multiple_incremental_adds(self) -> None:
        idx = BM25Index().fit(["initial document"])
        idx.add_documents(["second document"])
        idx.add_documents(["third document"])
        assert idx.n_docs == 3
        results = idx.query("third")
        assert results[0].doc_index == 2

    def test_add_to_empty_index(self) -> None:
        idx = BM25Index().fit([])
        idx.add_documents(["first document ever"])
        assert idx.n_docs == 1
        results = idx.query("first document")
        assert len(results) == 1


# ── Persistence tests (CP-2.1.6) ───────────────────────────────────────────


class TestPersistence:
    def test_save_and_load(self, fitted_index: BM25Index, tmp_path) -> None:
        path = tmp_path / "bm25.pkl"
        fitted_index.save(path)
        assert path.exists()

        loaded = BM25Index.load(path)
        assert loaded.n_docs == fitted_index.n_docs
        assert loaded.k1 == fitted_index.k1
        assert loaded.b == fitted_index.b
        assert loaded.vocabulary_size == fitted_index.vocabulary_size
        assert loaded._avg_doc_length == pytest.approx(fitted_index._avg_doc_length)

    def test_loaded_index_produces_same_results(
        self, fitted_index: BM25Index, tmp_path
    ) -> None:
        path = tmp_path / "bm25.pkl"
        fitted_index.save(path)
        loaded = BM25Index.load(path)

        original_results = fitted_index.query("Python programming", top_k=5)
        loaded_results = loaded.query("Python programming", top_k=5)

        assert len(original_results) == len(loaded_results)
        for orig, load in zip(original_results, loaded_results):
            assert orig.doc_index == load.doc_index
            assert orig.score == pytest.approx(load.score)
            assert orig.document == load.document

    def test_load_nonexistent_file(self, tmp_path) -> None:
        with pytest.raises(FileNotFoundError):
            BM25Index.load(tmp_path / "nonexistent.pkl")

    def test_save_creates_parent_directories(self, tmp_path) -> None:
        path = tmp_path / "nested" / "dir" / "bm25.pkl"
        idx = BM25Index().fit(["test"])
        idx.save(path)
        assert path.exists()

    def test_save_load_after_incremental_add(
        self, fitted_index: BM25Index, tmp_path
    ) -> None:
        fitted_index.add_documents(["Extra doc about networks"])
        path = tmp_path / "bm25_updated.pkl"
        fitted_index.save(path)
        loaded = BM25Index.load(path)
        assert loaded.n_docs == fitted_index.n_docs

        results = loaded.query("networks")
        assert any("networks" in r.document.lower() for r in results)

    def test_save_load_preserves_custom_params(self, tmp_path) -> None:
        idx = BM25Index(k1=2.0, b=0.5).fit(["custom params test"])
        path = tmp_path / "custom.pkl"
        idx.save(path)
        loaded = BM25Index.load(path)
        assert loaded.k1 == 2.0
        assert loaded.b == 0.5


# ── Edge-case and integration tests ────────────────────────────────────────


class TestEdgeCases:
    def test_duplicate_documents(self) -> None:
        idx = BM25Index().fit(["same text here", "same text here"])
        results = idx.query("same text")
        assert len(results) == 2
        assert results[0].score == pytest.approx(results[1].score)

    def test_very_long_document(self) -> None:
        long_doc = " ".join(["word"] * 10_000)
        idx = BM25Index().fit([long_doc, "short"])
        results = idx.query("word")
        assert len(results) >= 1

    def test_special_characters_in_query(self, fitted_index: BM25Index) -> None:
        results = fitted_index.query("Python!!! @#$% programming???")
        assert len(results) > 0

    def test_get_document(self, fitted_index: BM25Index) -> None:
        assert fitted_index.get_document(0) is not None
        assert fitted_index.get_document(999) is None
        assert fitted_index.get_document(-1) is None

    def test_custom_k1_b_parameters(self, sample_corpus: list[str]) -> None:
        idx1 = BM25Index(k1=1.0, b=0.5).fit(sample_corpus)
        idx2 = BM25Index(k1=2.0, b=1.0).fit(sample_corpus)
        r1 = idx1.query("Python programming")
        r2 = idx2.query("Python programming")
        assert r1[0].score != pytest.approx(r2[0].score)

    def test_numeric_tokens(self) -> None:
        idx = BM25Index().fit(["error code 404", "status 200 ok", "timeout 500"])
        results = idx.query("404")
        assert results[0].doc_index == 0

    def test_unicode_text(self) -> None:
        docs = ["café résumé naïve", "plain english text"]
        idx = BM25Index().fit(docs)
        results = idx.query("caf")
        assert len(results) >= 1
