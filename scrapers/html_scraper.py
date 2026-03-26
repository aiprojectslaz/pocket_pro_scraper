import requests
from bs4 import BeautifulSoup


def _extract_text(soup: BeautifulSoup) -> str:
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    for selector in ["main", "article", '[id="content"]', "body"]:
        el = soup.select_one(selector)
        if el:
            return el.get_text(separator="\n", strip=True)
    return soup.get_text(separator="\n", strip=True)


def scrape_html(url: str) -> str:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    text = _extract_text(soup)
    if not text:
        raise ValueError(f"No text extracted from URL: {url}")
    return text


def scrape_html_file(filepath: str) -> str:
    with open(filepath, encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")
    text = _extract_text(soup)
    if not text:
        raise ValueError(f"No text extracted from file: {filepath}")
    return text
