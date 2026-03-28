"""
Generic HTML scraper — fallback for unregistered domains.

Strips navigation/chrome and returns the main content as plain text.
Used by the domain router when no site-specific scraper is registered,
and by batch mode when reading local .html files from sources/html/.
"""

from bs4 import BeautifulSoup
from .base import fetch_soup, get_text


def _extract_text(soup: BeautifulSoup) -> str:
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    for selector in ["main", "article", '[id="content"]', "body"]:
        el = soup.select_one(selector)
        if el:
            return el.get_text(separator="\n", strip=True)
    return soup.get_text(separator="\n", strip=True)


def scrape(url: str) -> str:
    """Fetch a URL and return plain extracted text (no structured parsing)."""
    soup = fetch_soup(url)
    text = _extract_text(soup)
    if not text:
        raise ValueError(f"No text extracted from URL: {url}")
    return text


def scrape_file(filepath: str) -> str:
    """Read a local HTML file and return plain extracted text."""
    with open(filepath, encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")
    text = _extract_text(soup)
    if not text:
        raise ValueError(f"No text extracted from file: {filepath}")
    return text
