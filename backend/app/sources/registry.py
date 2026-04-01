import logging
from typing import Optional

from app.sources.base import SourceAdapter

logger = logging.getLogger(__name__)


class SourceRegistry:
    """Maintains a mapping of registered source adapters by name."""

    def __init__(self) -> None:
        self._adapters: dict[str, SourceAdapter] = {}

    def register(self, adapter: SourceAdapter) -> None:
        logger.info(
            "Registered source adapter: %s (%s)",
            adapter.name,
            adapter.display_name,
        )
        self._adapters[adapter.name] = adapter

    def get(self, name: str) -> Optional[SourceAdapter]:
        return self._adapters.get(name)

    def get_all(self) -> list[SourceAdapter]:
        return list(self._adapters.values())

    def get_available(self) -> list[SourceAdapter]:
        return [a for a in self._adapters.values() if a.is_available()]
