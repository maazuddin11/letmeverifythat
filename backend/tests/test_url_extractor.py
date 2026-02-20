"""Tests for url_extractor: URL detection, HTML cleaning, and URL fetching."""

import pytest
import httpx
import respx

from url_extractor import extract_urls, _clean_html, fetch_url_text


# ---------------------------------------------------------------------------
# extract_urls
# ---------------------------------------------------------------------------

class TestExtractUrls:
    def test_no_urls(self):
        urls, remaining = extract_urls("turmeric cures cancer")
        assert urls == []
        assert remaining == "turmeric cures cancer"

    def test_single_url_alone(self):
        urls, remaining = extract_urls("https://example.com/article")
        assert urls == ["https://example.com/article"]
        assert remaining == ""

    def test_single_url_with_surrounding_text(self):
        text = "Check this https://example.com/article and tell me"
        urls, remaining = extract_urls(text)
        assert urls == ["https://example.com/article"]
        assert "Check this" in remaining
        assert "and tell me" in remaining
        assert "https://example.com/article" not in remaining

    def test_multiple_urls(self):
        text = "https://one.com\nhttps://two.com\nhttps://three.com"
        urls, remaining = extract_urls(text)
        assert urls == ["https://one.com", "https://two.com", "https://three.com"]

    def test_duplicate_urls_deduped(self):
        text = "https://example.com and again https://example.com"
        urls, remaining = extract_urls(text)
        assert urls == ["https://example.com"]

    def test_url_with_trailing_punctuation(self):
        text = "See https://example.com/page. Also https://other.com/path, ok?"
        urls, remaining = extract_urls(text)
        assert "https://example.com/page" in urls
        assert "https://other.com/path" in urls
        # Trailing period/comma should not be part of the URL
        for url in urls:
            assert not url.endswith(".")
            assert not url.endswith(",")

    def test_url_with_query_params(self):
        text = "Visit https://example.com/search?q=health&page=1 for info"
        urls, remaining = extract_urls(text)
        assert urls == ["https://example.com/search?q=health&page=1"]

    def test_http_url(self):
        urls, _ = extract_urls("http://insecure.example.com/page")
        assert urls == ["http://insecure.example.com/page"]

    def test_mixed_urls_and_claims(self):
        text = (
            "https://example.com/health\n"
            "MSG causes headaches\n"
            "https://another.com/article\n"
            "Turmeric cures cancer"
        )
        urls, remaining = extract_urls(text)
        assert len(urls) == 2
        assert "MSG causes headaches" in remaining
        assert "Turmeric cures cancer" in remaining

    def test_empty_string(self):
        urls, remaining = extract_urls("")
        assert urls == []
        assert remaining == ""

    def test_whitespace_only(self):
        urls, remaining = extract_urls("   \n\n  ")
        assert urls == []


# ---------------------------------------------------------------------------
# _clean_html
# ---------------------------------------------------------------------------

class TestCleanHtml:
    def test_extracts_body_text(self):
        html = "<html><body><p>Hello world</p></body></html>"
        assert "Hello world" in _clean_html(html)

    def test_strips_scripts_and_styles(self):
        html = """
        <html><body>
            <script>alert('xss')</script>
            <style>.red { color: red; }</style>
            <p>Actual content</p>
        </body></html>
        """
        result = _clean_html(html)
        assert "Actual content" in result
        assert "alert" not in result
        assert ".red" not in result

    def test_strips_nav_footer_header(self):
        html = """
        <html><body>
            <nav><a href="/">Home</a></nav>
            <article><p>Article text here</p></article>
            <footer>Copyright 2024</footer>
        </body></html>
        """
        result = _clean_html(html)
        assert "Article text here" in result
        assert "Home" not in result
        assert "Copyright" not in result

    def test_prefers_article_tag(self):
        html = """
        <html><body>
            <div>Sidebar junk</div>
            <article><p>The real article content</p></article>
            <div>More junk</div>
        </body></html>
        """
        result = _clean_html(html)
        assert "The real article content" in result
        assert "Sidebar junk" not in result

    def test_prefers_main_tag(self):
        html = """
        <html><body>
            <div>Sidebar</div>
            <main><p>Main content</p></main>
            <div>Footer stuff</div>
        </body></html>
        """
        result = _clean_html(html)
        assert "Main content" in result
        assert "Sidebar" not in result

    def test_collapses_blank_lines(self):
        html = "<html><body><p>Line 1</p><br><br><br><br><p>Line 2</p></body></html>"
        result = _clean_html(html)
        assert "\n\n\n" not in result

    def test_truncates_long_content(self):
        html = "<html><body><p>" + "x" * 100_000 + "</p></body></html>"
        result = _clean_html(html)
        assert len(result) <= 80_000


# ---------------------------------------------------------------------------
# fetch_url_text
# ---------------------------------------------------------------------------

class TestFetchUrlText:
    @pytest.mark.asyncio
    async def test_invalid_url_raises(self):
        with pytest.raises(ValueError, match="Invalid URL"):
            await fetch_url_text("not-a-url")

    @pytest.mark.asyncio
    async def test_ftp_url_raises(self):
        with pytest.raises(ValueError, match="Invalid URL"):
            await fetch_url_text("ftp://files.example.com/data.txt")

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetches_html_page(self):
        html = "<html><body><article><p>Turmeric does not cure cancer.</p></article></body></html>"
        respx.get("https://example.com/article").mock(
            return_value=httpx.Response(
                200,
                text=html,
                headers={"content-type": "text/html; charset=utf-8"},
            )
        )
        result = await fetch_url_text("https://example.com/article")
        assert "Turmeric does not cure cancer" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_non_html_raises(self):
        respx.get("https://example.com/data.json").mock(
            return_value=httpx.Response(
                200,
                text='{"key": "value"}',
                headers={"content-type": "application/json"},
            )
        )
        with pytest.raises(ValueError, match="does not point to an HTML page"):
            await fetch_url_text("https://example.com/data.json")

    @pytest.mark.asyncio
    @respx.mock
    async def test_http_error_raises(self):
        respx.get("https://example.com/missing").mock(
            return_value=httpx.Response(404)
        )
        with pytest.raises(httpx.HTTPStatusError):
            await fetch_url_text("https://example.com/missing")

    @pytest.mark.asyncio
    @respx.mock
    async def test_empty_page_raises(self):
        html = "<html><body></body></html>"
        respx.get("https://example.com/empty").mock(
            return_value=httpx.Response(
                200,
                text=html,
                headers={"content-type": "text/html"},
            )
        )
        with pytest.raises(ValueError, match="Could not extract any readable text"):
            await fetch_url_text("https://example.com/empty")
