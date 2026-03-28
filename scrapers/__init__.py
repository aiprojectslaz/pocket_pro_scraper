"""
Scraper registry — routes URLs to the correct site-specific scraper
based on domain. Falls back to generic text extraction for unregistered domains.

To add support for a new website:
  1. Create scrapers/<name>.py exporting def scrape(url: str) -> dict
  2. Add one line to SCRAPERS below: "domain.tld": scrape_<name>
"""

from urllib.parse import urlparse

from .ontario_laws import scrape as scrape_ontario
from .federal_laws import scrape as scrape_federal
from .html_scraper import scrape as scrape_generic, scrape_file as scrape_html_file
from .pdf_scraper import scrape_pdf
from .xml_scraper import scrape_xml

# Map bare domain (no www.) → scraper function
SCRAPERS: dict = {
    "ontario.ca": scrape_ontario,
    "laws-lois.justice.gc.ca": scrape_federal,
}


def scrape_html(url: str) -> dict | str:
    """
    Route a URL to the appropriate site-specific scraper.
    Returns a dict for registered domains (structured data),
    or a plain str for unregistered domains (generic text extraction).
    """
    domain = urlparse(url).netloc.replace("www.", "")
    scraper = SCRAPERS.get(domain)
    if scraper:
        return scraper(url)
    # Fallback: generic text extraction — output goes through Claude
    return scrape_generic(url)


__all__ = [
    "scrape_html",
    "scrape_html_file",
    "scrape_pdf",
    "scrape_xml",
    "SCRAPERS",
]
