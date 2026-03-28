"""
Scraper for Ontario e-Laws (ontario.ca/laws).

Parses the DOM class structure used by the Ontario e-Laws site:
  section > headnote / subsection > paragraph / Pnote

NOTE: The ontario.ca site requires JavaScript to render. This scraper works
correctly on the rendered DOM (e.g. a saved HTML file or via Playwright).
A plain requests fetch will return a JS-wall page with no sections.
"""

from bs4 import BeautifulSoup
from .base import fetch_soup, get_text


def _parse(soup: BeautifulSoup) -> dict:
    act_title = ""
    title_el = soup.select_one("h1, .act-title, #act-title")
    if title_el:
        act_title = get_text(title_el)

    sections = []
    current_section = None
    current_subsection = None

    for el in soup.find_all(True):
        classes = el.get("class", [])

        if "section" in classes:
            bold = el.find("b")
            # Store only the element's immediate text children to avoid
            # duplicating subsection content at the section level.
            current_section = {
                "section_number": get_text(bold) if bold else "",
                "title": "",
                "text": get_text(el),
                "subsections": [],
                "note": "",
            }
            current_subsection = None
            sections.append(current_section)

        elif "headnote" in classes:
            if current_section:
                current_section["title"] = el.get_text(strip=True)

        elif "subsection" in classes:
            if current_section:
                current_subsection = {
                    "text": get_text(el),
                    "paragraphs": [],
                    "note": "",
                }
                current_section["subsections"].append(current_subsection)

        elif "paragraph" in classes:
            if current_subsection:
                current_subsection["paragraphs"].append(get_text(el))

        elif "Pnote" in classes:
            target = current_subsection or current_section
            if target:
                target["note"] = el.get_text(strip=True)

    return {"act": act_title, "sections": sections}


def scrape(url: str) -> dict:
    soup = fetch_soup(url)
    result = _parse(soup)
    if not result["sections"]:
        raise ValueError(
            f"No sections found at {url}. "
            "ontario.ca requires JavaScript — use a saved/rendered HTML file if scraping live."
        )
    return result


def scrape_file(filepath: str) -> dict:
    with open(filepath, encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")
    result = _parse(soup)
    if not result["sections"]:
        raise ValueError(f"No sections extracted from file: {filepath}")
    return result
