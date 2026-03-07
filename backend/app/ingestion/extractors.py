"""Content extraction from HTML, raw text, and snippets."""

from __future__ import annotations

import logging
import re
import unicodedata

from bs4 import BeautifulSoup
from readability import Document as ReadabilityDocument

logger = logging.getLogger(__name__)


class ContentExtractor:
    """Extracts clean text content from various input formats.

    Provides three extraction paths:
    - HTML: readability-based main-content extraction + BeautifulSoup tag stripping
    - Plain text: whitespace normalisation and unicode cleanup
    - Snippet: lightweight pass-through for when full content is unavailable
    """

    @staticmethod
    def extract_from_html(html: str) -> str:
        """Extract main readable content from an HTML document.

        Uses *readability-lxml* to isolate the article body, then strips
        remaining tags with BeautifulSoup.  Falls back to naive tag stripping
        when readability fails (e.g. malformed markup).
        """
        if not html or not html.strip():
            return ""

        try:
            doc = ReadabilityDocument(html)
            summary_html = doc.summary()
            soup = BeautifulSoup(summary_html, "html.parser")
            text = soup.get_text(separator="\n")
        except Exception:
            logger.warning(
                "Readability extraction failed; falling back to basic HTML stripping"
            )
            soup = BeautifulSoup(html, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            text = soup.get_text(separator="\n")

        return ContentExtractor._clean_text(text)

    @staticmethod
    def extract_from_text(text: str) -> str:
        """Normalise unicode and clean whitespace from plain text."""
        if not text:
            return ""
        return ContentExtractor._clean_text(text)

    @staticmethod
    def extract_from_snippet(snippet: str, url: str = "") -> str:
        """Return the snippet as-is (after basic cleanup).

        Used when the full page content could not be fetched.
        """
        if not snippet:
            return ""
        return ContentExtractor._clean_text(snippet)

    @staticmethod
    def _clean_text(text: str) -> str:
        """Shared post-processing: null-byte removal, unicode NFC, whitespace collapse."""
        text = text.replace("\x00", "")
        text = unicodedata.normalize("NFC", text)
        text = re.sub(r"[\t\r\f\v]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r" {2,}", " ", text)
        lines = [line.strip() for line in text.split("\n")]
        text = "\n".join(lines)
        return text.strip()
