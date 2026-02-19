"""Service to fetch a URL and extract readable text content."""

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

# Max content length to send to the claim extractor (roughly ~15k words)
MAX_TEXT_LENGTH = 80_000

# Request headers to look like a normal browser (some sites block bare httpx)
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; LetMeVerifyThat/1.0; +https://github.com/LetMeVerifyThat)"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def is_url(text: str) -> bool:
    """Return True if the text looks like a single URL."""
    text = text.strip()
    if " " in text or "\n" in text:
        return False
    try:
        parsed = urlparse(text)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


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


async def extract_text_from_url(url: str) -> str:
    """
    Fetch a URL and return its readable text content.

    Raises:
        ValueError: If the URL is invalid or the page cannot be fetched.
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
