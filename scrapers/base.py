"""Shared utilities for all site-specific scrapers."""

import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0"}


def fetch_soup(url: str) -> BeautifulSoup:
    """Fetch a URL and return a parsed BeautifulSoup object."""
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def get_text(el) -> str:
    """Return stripped text from a BeautifulSoup element."""
    return el.get_text(separator=" ", strip=True) if el else ""
