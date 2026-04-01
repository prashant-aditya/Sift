"""Celery application configuration for Sift workers."""

from __future__ import annotations

import os

from celery import Celery


def _env(name: str, default: str) -> str:
    val = os.getenv(name)
    return val if val is not None and val != "" else default


def _redis_url_fallback(default: str) -> str:
    """
    Prefer explicit Celery URLs, but fall back to UPSTASH_REDIS_URL for
    free-tier deployments where a single Redis URL is provided.
    """
    return _env("UPSTASH_REDIS_URL", default)


celery_app = Celery(
    "sift",
    broker=_env("CELERY_BROKER_URL", _redis_url_fallback("redis://redis:6379/0")),
    backend=_env(
        "CELERY_RESULT_BACKEND", _redis_url_fallback("redis://redis:6379/0")
    ),
    include=["workers.tasks", "workers.callbacks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    enable_utc=True,
    timezone="UTC",
    task_soft_time_limit=15,
    task_time_limit=20,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "workers.tasks.search_source": {"queue": "search"},
        "workers.callbacks.process_results": {"queue": "ingestion"},
        "workers.tasks.refresh_research": {"queue": "ingestion"},
    },
)
