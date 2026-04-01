from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SourceResult(BaseModel):
    """A single result returned by a source adapter."""

    title: str
    url: str
    snippet: str
    raw_content: Optional[str] = None
    source_name: str
    published_date: Optional[datetime] = None
    metadata: dict = Field(default_factory=dict)


class SourceAdapter(ABC):
    """Abstract base for all source adapters.

    Subclasses must set ``name`` and ``display_name`` as class attributes and
    implement ``search`` and ``is_available``.
    """

    name: str
    display_name: str
    max_results: int = 10
    timeout_seconds: int = 10

    @abstractmethod
    async def search(
        self, query: str, max_results: Optional[int] = None
    ) -> list[SourceResult]:
        """Run a search and return structured results."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Return ``True`` when the adapter is ready to serve requests."""
        ...
