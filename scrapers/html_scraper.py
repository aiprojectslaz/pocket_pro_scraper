import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0"}


def _parse_act_structure(soup: BeautifulSoup) -> dict:
    act_title = ""
    title_el = soup.select_one("h1, .act-title, #act-title")
    if title_el:
        act_title = title_el.get_text(strip=True)

    sections = []
    current_section = None
    current_subsection = None

    for el in soup.find_all(True):
        classes = el.get("class", [])

        if "section" in classes:
            bold = el.find("b")
            current_section = {
                "section_number": bold.get_text(strip=True) if bold else "",
                "title": "",
                # Store only the element's own direct text, not child elements,
                # to avoid duplicating subsection content at the section level.
                "text": el.get_text(separator=" ", strip=True),
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
                    "text": el.get_text(separator=" ", strip=True),
                    "paragraphs": [],
                    "note": "",
                }
                current_section["subsections"].append(current_subsection)

        elif "paragraph" in classes:
            if current_subsection:
                current_subsection["paragraphs"].append(
                    el.get_text(separator=" ", strip=True)
                )

        elif "Pnote" in classes:
            target = current_subsection or current_section
            if target:
                target["note"] = el.get_text(strip=True)

    return {"act": act_title, "sections": sections}


def scrape_html(url: str) -> dict:
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    result = _parse_act_structure(soup)
    if not result["sections"]:
        raise ValueError(f"No sections extracted from URL: {url}")
    return result


def scrape_html_file(filepath: str) -> dict:
    with open(filepath, encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")
    result = _parse_act_structure(soup)
    if not result["sections"]:
        raise ValueError(f"No sections extracted from file: {filepath}")
    return result
