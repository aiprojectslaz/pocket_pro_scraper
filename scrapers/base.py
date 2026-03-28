"""Shared utilities for all site-specific scrapers."""

import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0"}


def fetch_soup(url: str) -> BeautifulSoup:
    """Fetch a URL and return a parsed BeautifulSoup object."""
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def fetch_soup_js(url: str, wait_for: str | None = None) -> BeautifulSoup:
    """Fetch a JS-rendered page using Playwright headless Chromium."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise ImportError(
            "playwright is not installed. Run:\n"
            "  pip install playwright\n"
            "  playwright install chromium"
        )
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle", timeout=60000)
        if wait_for:
            page.wait_for_selector(wait_for, timeout=15000)
        html = page.content()
        browser.close()
    return BeautifulSoup(html, "html.parser")


def get_text(el) -> str:
    """Return stripped text from a BeautifulSoup element."""
    return el.get_text(separator=" ", strip=True) if el else ""
