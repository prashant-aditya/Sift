"""Retrieval strategies for the Sift research engine.

This package uses lazy imports to avoid circular dependencies between
retrieval modules and the vector store / ingestion pipeline.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = ["DenseRetriever", "HybridRetriever", "MinHashDeduplicator"]


def __getattr__(name: str) -> Any:  # pragma: no cover
    if name == "DenseRetriever":
        return import_module("app.retrieval.dense").DenseRetriever
    if name == "HybridRetriever":
        return import_module("app.retrieval.hybrid_retriever").HybridRetriever
    if name == "MinHashDeduplicator":
        return import_module("app.retrieval.deduplication").MinHashDeduplicator
    raise AttributeError(name)
