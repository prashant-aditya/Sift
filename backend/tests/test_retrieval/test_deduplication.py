"""Tests for near-duplicate detection (Goal 2.3)."""

from __future__ import annotations

import pytest

from app.retrieval.deduplication import DedupItem, MinHashDeduplicator


class TestMinHashDeduplicator:
    def test_identical_docs_detected(self) -> None:
        pytest.importorskip("datasketch")
        d = MinHashDeduplicator(num_perm=128, threshold=0.8)
        texts = [
            "Sift is a research engine that deduplicates results before embedding.",
            "Sift is a research engine that deduplicates results before embedding.",
        ]
        groups = d.find_duplicates(texts)
        assert len(groups) == 1
        assert groups[0] == {0, 1}

    def test_rephrased_docs_detected(self) -> None:
        pytest.importorskip("datasketch")
        d = MinHashDeduplicator(num_perm=128, threshold=0.8)
        # Keep most 3-grams intact but introduce small edits.
        a = "Sift runs extraction then deduplication then chunking then embedding for retrieval quality."
        b = "Sift runs extraction then deduplication then chunking then embedding for high retrieval quality."
        groups = d.find_duplicates([a, b])
        assert groups and {0, 1} in groups

    def test_different_docs_not_flagged(self) -> None:
        pytest.importorskip("datasketch")
        d = MinHashDeduplicator(num_perm=128, threshold=0.8)
        a = "Cats chase lasers and sleep on keyboards."
        b = "Kubernetes schedules containers across nodes with a control plane."
        groups = d.find_duplicates([a, b])
        assert groups == []

    def test_authority_selection(self) -> None:
        pytest.importorskip("datasketch")
        d = MinHashDeduplicator(num_perm=128, threshold=0.8)
        items = [
            DedupItem(
                text="Sift runs extraction then deduplication then chunking then embedding.",
                source_name="duckduckgo",
                item_id="ddg",
            ),
            DedupItem(
                text="Sift runs extraction then deduplication then chunking then embedding.",
                source_name="wikipedia",
                item_id="wiki",
            ),
        ]
        kept = d.deduplicate(items)
        assert len(kept) == 1
        assert kept[0].source_name == "wikipedia"

