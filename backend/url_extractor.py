"""Service to find URLs in user text, fetch them, and extract readable content."""

import re
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

# Elements that don't contain article text
STRIP_TAGS = [
    "script",
    "style",
    "nav",
    "footer",
    "header",
    "aside",
    "noscript",
    "iframe",
    "svg",
    "form",
    "button",
]

# Max content length per URL (roughly ~15k words)
MAX_TEXT_LENGTH = 80_000

# Request headers to look like a normal browser (some sites block bare httpx)
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; LetMeVerifyThat/1.0; +https://github.com/LetMeVerifyThat)"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# Regex that matches http/https URLs in free-form text
_URL_RE = re.compile(r"https?://[^\s<>\"']+")


def extract_urls(text: str) -> tuple[list[str], str]:
    """
    Find all URLs in *text* and return (urls, remaining_text).

    The remaining text has the URLs stripped out and excess whitespace collapsed.
    """
    urls: list[str] = []
    seen: set[str] = set()
    for match in _URL_RE.finditer(text):
        url = match.group(0).rstrip(".,;:!?)\"'")
        if url not in seen:
            urls.append(url)
            seen.add(url)

    if not urls:
        return [], text

    # Remove each URL occurrence from the text
    remaining = text
    for url in urls:
        remaining = remaining.replace(url, "")

    # Collapse leftover blank lines / extra spaces
    remaining = re.sub(r"\n{3,}", "\n\n", remaining).strip()
    return urls, remaining


def _clean_html(html: str) -> str:
    """Parse HTML and extract readable text, stripping boilerplate elements."""
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup.find_all(STRIP_TAGS):
        tag.decompose()

    # Prefer <article> or <main> content if present
    article = soup.find("article") or soup.find("main")
    root = article if article else soup.body if soup.body else soup

    text = root.get_text(separator="\n", strip=True)

    # Collapse multiple blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text[:MAX_TEXT_LENGTH]


async def fetch_url_text(url: str) -> str:
    """
    Fetch a single URL and return its readable text content.

    Raises httpx.HTTPStatusError on HTTP failures, ValueError on non-HTML or
    empty pages.
    """
    url = url.strip()
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError(f"Invalid URL: {url}")

    async with httpx.AsyncClient(
        timeout=30.0,
        follow_redirects=True,
        headers=REQUEST_HEADERS,
    ) as client:
        response = await client.get(url)
        response.raise_for_status()

    content_type = response.headers.get("content-type", "")
    if "text/html" not in content_type and "application/xhtml" not in content_type:
        raise ValueError(
            f"URL does not point to an HTML page (content-type: {content_type})"
        )

    text = _clean_html(response.text)
    if not text.strip():
        raise ValueError("Could not extract any readable text from the page")

    return text
