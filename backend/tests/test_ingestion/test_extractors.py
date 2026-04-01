"""Tests for ContentExtractor: HTML extraction, text cleaning, snippet pass-through."""

from app.ingestion.extractors import ContentExtractor


class TestExtractFromHtml:
    def test_basic_article(self):
        html = """
        <html><head><title>Test</title></head>
        <body>
            <nav>Menu links</nav>
            <article>
                <h1>Hello World</h1>
                <p>This is the main content of the article.</p>
                <p>It has multiple paragraphs with useful information.</p>
            </article>
            <footer>Copyright 2025</footer>
        </body></html>
        """
        result = ContentExtractor.extract_from_html(html)
        assert "main content" in result
        assert "multiple paragraphs" in result

    def test_strips_script_and_style(self):
        html = """
        <html><body>
            <script>alert('xss');</script>
            <style>.hidden { display: none; }</style>
            <p>Visible content here.</p>
        </body></html>
        """
        result = ContentExtractor.extract_from_html(html)
        assert "alert" not in result
        assert "display: none" not in result
        assert "Visible content" in result

    def test_empty_html_returns_empty(self):
        assert ContentExtractor.extract_from_html("") == ""
        assert ContentExtractor.extract_from_html("   ") == ""

    def test_malformed_html(self):
        html = "<p>Unclosed paragraph <div>with nested <b>tags"
        result = ContentExtractor.extract_from_html(html)
        assert "Unclosed paragraph" in result or "nested" in result

    def test_null_bytes_stripped(self):
        html = "<html><body><p>Has \x00 null \x00 bytes</p></body></html>"
        result = ContentExtractor.extract_from_html(html)
        assert "\x00" not in result
        assert "null" in result


class TestExtractFromText:
    def test_normalises_whitespace(self):
        text = "Hello   world\t\there\r\nand more"
        result = ContentExtractor.extract_from_text(text)
        assert "Hello world" in result
        assert "\t" not in result

    def test_collapses_excessive_newlines(self):
        text = "Para one.\n\n\n\n\nPara two."
        result = ContentExtractor.extract_from_text(text)
        assert "\n\n\n" not in result
        assert "Para one." in result
        assert "Para two." in result

    def test_unicode_normalisation(self):
        text = "caf\u00e9"  # NFC composed form
        result = ContentExtractor.extract_from_text(text)
        assert result == "café"

    def test_empty_string(self):
        assert ContentExtractor.extract_from_text("") == ""

    def test_null_bytes(self):
        result = ContentExtractor.extract_from_text("clean\x00text")
        assert "\x00" not in result
        assert "cleantext" in result


class TestExtractFromSnippet:
    def test_returns_cleaned_snippet(self):
        snippet = "  This is a search snippet.  "
        result = ContentExtractor.extract_from_snippet(
            snippet, url="https://example.com"
        )
        assert result == "This is a search snippet."

    def test_empty_snippet(self):
        assert ContentExtractor.extract_from_snippet("") == ""

    def test_snippet_with_special_chars(self):
        snippet = "Result with \x00 null and   extra   spaces"
        result = ContentExtractor.extract_from_snippet(snippet)
        assert "\x00" not in result
        assert "extra spaces" in result
