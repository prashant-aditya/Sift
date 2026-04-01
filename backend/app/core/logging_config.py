from __future__ import annotations

import logging
import logging.config
import os
from datetime import datetime, timezone
from typing import Any

from app.core.log_context import get_request_id, get_session_id


class ContextAwareFormatter(logging.Formatter):
    """Formatter that appends request/session correlation ids when present."""

    def format(self, record: logging.LogRecord) -> str:
        record.request_id = getattr(record, "request_id", None) or get_request_id()  # type: ignore[attr-defined]
        record.session_id = getattr(record, "session_id", None) or get_session_id()  # type: ignore[attr-defined]
        return super().format(record)


class UtcIsoTimeFormatter(ContextAwareFormatter):
    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        dt = datetime.fromtimestamp(record.created, tz=timezone.utc)
        return dt.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def setup_logging(*, default_level: str = "INFO") -> None:
    """
    Configure application + uvicorn loggers consistently.

    Environment variables:
    - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR
    - LOG_FORMAT: text|json
    """
    level = (os.getenv("LOG_LEVEL") or default_level).upper()
    log_format = (os.getenv("LOG_FORMAT") or "text").lower().strip()

    if log_format == "json":
        import structlog

        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.processors.add_log_level,
                structlog.processors.TimeStamper(fmt="iso", utc=True),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.JSONRenderer(),
            ],
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

        # Keep stdlib logging minimal; structlog emits JSON.
        logging.basicConfig(level=level)
        return

    config: dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "()": "app.core.logging_config.UtcIsoTimeFormatter",
                "format": "%(asctime)s %(levelname)s %(name)s"
                " request_id=%(request_id)s session_id=%(session_id)s - %(message)s",
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "standard",
                "level": level,
            }
        },
        "root": {"handlers": ["console"], "level": level},
        "loggers": {
            # Ensure uvicorn logs go through our formatter/handler.
            "uvicorn": {"level": level, "handlers": ["console"], "propagate": False},
            "uvicorn.error": {
                "level": level,
                "handlers": ["console"],
                "propagate": False,
            },
            "uvicorn.access": {
                "level": level,
                "handlers": ["console"],
                "propagate": False,
            },
        },
    }

    logging.config.dictConfig(config)
