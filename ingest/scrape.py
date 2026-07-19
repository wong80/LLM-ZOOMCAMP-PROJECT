"""
Sitemap-based documentation scraper.

Fetches a library's sitemap.xml to discover all doc pages, then scrapes
each page for title, breadcrumbs, and HTML content. Uses httpx for HTTP
and BeautifulSoup for parsing.
"""

import re
import warnings
import httpx
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
from urllib.parse import urlparse

# Suppress the harmless "XML parsed as HTML" warning when parsing sitemaps
# with the html.parser (which works fine for simple XML sitemaps).
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

SITEMAP_URL = "https://fastapi.tiangolo.com/sitemap.xml"

# Identify ourselves so doc hosts can contact us if there's an issue
USER_AGENT = (
    "Mozilla/5.0 (compatible; PyDocAssistant/1.0; "
    "+https://github.com/wong80/llm-zoomcamp-project)"
)


def _fetch(url: str, client: httpx.Client | None = None) -> str:
    """
    Fetch a URL and return the response text.

    Accepts an optional shared httpx.Client for connection reuse.
    If no client is provided, creates and closes one automatically.
    Raises RuntimeError on HTTP errors or network failures.
    """
    close_client = client is None
    if client is None:
        client = httpx.Client(headers={"User-Agent": USER_AGENT}, follow_redirects=True, timeout=30.0)
    try:
        resp = client.get(url)
        resp.raise_for_status()
        return resp.text
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"HTTP {e.response.status_code} fetching {url}") from e
    except httpx.RequestError as e:
        raise RuntimeError(f"Request failed for {url}: {e}") from e
    finally:
        if close_client:
            client.close()


def get_doc_urls(sitemap_url: str = SITEMAP_URL, client: httpx.Client | None = None) -> list[str]:
    """
    Parse a sitemap XML and return all doc page URLs.

    Filters to only URLs whose path ends with '/' — this excludes
    assets like /img/favicon.ico and keeps only actual documentation pages.
    Returns sorted unique URLs.
    """
    xml = _fetch(sitemap_url, client=client)
    # html.parser works fine for the simple XML structure of sitemaps
    soup = BeautifulSoup(xml, "html.parser")
    urls = []
    for loc in soup.find_all("loc"):
        url = loc.get_text(strip=True)
        parsed = urlparse(url)
        # Doc pages on ReadTheDocs/Sphinx end with trailing slash
        if parsed.path.endswith("/"):
            urls.append(url)
    return sorted(set(urls))


def scrape_page(url: str, client: httpx.Client | None = None) -> dict:
    """
    Scrape a single documentation page.

    Returns a dict with:
        url          — the page URL
        title        — text of the <h1> element
        breadcrumbs  — list of breadcrumb link texts (from <nav class="breadcrumb">)
        content_html — inner HTML of the main content div (or <body> as fallback)

    The content_html is passed to the chunker for further processing.
    """
    html = _fetch(url, client=client)
    soup = BeautifulSoup(html, "html.parser")

    # Extract page title from the first <h1>
    title_tag = soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else ""

    # Extract breadcrumbs for section context
    breadcrumbs = []
    bc_nav = soup.find("nav", class_=re.compile(r"breadcrumb", re.I))
    if bc_nav:
        breadcrumbs = [a.get_text(strip=True) for a in bc_nav.find_all("a")]

    # Find the main content area — try common content class names,
    # fall back to the full <body> if none match
    content_div = soup.find("div", class_=re.compile(r"content|documentation|doc|article", re.I))
    if content_div is None:
        content_div = soup.find("body")

    content_html = str(content_div) if content_div else ""

    return {
        "url": url,
        "title": title,
        "breadcrumbs": breadcrumbs,
        "content_html": content_html,
    }
