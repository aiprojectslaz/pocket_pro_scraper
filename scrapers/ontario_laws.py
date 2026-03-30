"""
Scraper for Ontario e-Laws (ontario.ca/laws).

Parses the DOM class structure used by the Ontario e-Laws site:
  section > headnote / subsection > paragraph / Pnote
"""

import re

from bs4 import BeautifulSoup
from .base import fetch_soup_js, get_text


def _first_text(soup: BeautifulSoup, selector: str, fallback_substr: str) -> str:
    el = soup.select_one(selector)
    if not el and fallback_substr:
        el = next(
            (p for p in soup.find_all("p") if fallback_substr in p.get_text()),
            None,
        )
    return el.get_text(strip=True) if el else ""


def _parse(soup: BeautifulSoup) -> dict:
    # Title
    act_title = ""
    title_el = soup.select_one("title")
    if title_el:
        act_title = title_el.get_text(strip=True).split(" | ")[0].strip()

    short_title = _first_text(soup, "p.shorttitle", "")
    chapter = _first_text(soup, "p.chapter", "Chapter")

    # Dates
    combined_el = soup.select_one("p.DocVer") or next(
        (p for p in soup.find_all("p") if "Consolidation period" in p.get_text()), None
    )
    combined = combined_el.get_text(strip=True) if combined_el else ""

    m = re.search(r'Consolidation period[^A-Za-z]+([A-Za-z].*?)\s*-\s*e-Laws', combined)
    version_date = m.group(1).strip() if m else combined

    m2 = re.search(r'e-Laws currency date[^A-Za-z(]*\(?([A-Za-z].*?)\)?$', combined)
    currency_date = m2.group(1).strip() if m2 else ""

    last_amended_raw = _first_text(soup, "p.lastAmendDate", "Last amendment")
    last_amended = re.sub(
        r'^Last amendment\s*[:\s]+', '', last_amended_raw, flags=re.IGNORECASE
    ).strip()

    # Regulations
    regulations = []
    reg_div = soup.select_one("#reg-content")
    if reg_div:
        labels = reg_div.select('[class*="volume-label"]')
        titles = reg_div.select('[class*="doc-row__title"]')

        for i, label_el in enumerate(labels):
            number = label_el.get_text(strip=True)
            title = titles[i].get_text(strip=True) if i < len(titles) else ""
            if number or title:
                regulations.append({"number": number, "title": title})

    # Sections
    sections = []
    current_section = None
    current_subsection = None
    pending_headnote = ""

    for el in soup.find_all(True):
        classes = el.get("class", [])

        # SECTION
        if "section" in classes:
            bold = el.find("b")
            current_section = {
                "section_number": get_text(bold) if bold else "",
                "title": pending_headnote,
                "text": get_text(el),
                "subsections": [],
                "note": "",
            }
            pending_headnote = ""
            current_subsection = None
            sections.append(current_section)

        # HEADNOTE
        elif "headnote" in classes:
            pending_headnote = el.get_text(strip=True)

        # ✅ DEFINITIONS (CORRECT SOURCE)
        elif el.name == "p" and "definition" in classes:
            if current_section:
                text_full = get_text(el)

                match = re.match(r'^[“"](.*?)[”"]\s+(means|includes)\s+(.*)$', text_full)

                if match:
                    term = match.group(1).strip()
                    keyword = match.group(2)
                    definition_text = match.group(3).strip()

                    # Extract translation
                    translation_match = re.search(
                        r'\(\s*[“"](.*?)[”"]\s*\)\s*$', definition_text
                    )

                    if translation_match:
                        translation = translation_match.group(1).strip()
                        definition_text = re.sub(
                            r'\(\s*[“"].*?[”"]\s*\)\s*$', '', definition_text
                        ).strip()
                    else:
                        translation = ""

                    current_subsection = {
                        "text": f'“{term}”,',
                        "paragraphs": f"{keyword} {definition_text}",
                        "translation": translation,
                        "note": "",
                    }

                else:
                    current_subsection = {
                        "text": text_full,
                        "paragraphs": "",
                        "note": "",
                    }

                current_section["subsections"].append(current_subsection)

        # SUBSECTION (non-definition)
        elif "subsection" in classes:
            if current_section:
                current_subsection = {
                    "text": get_text(el),
                    "paragraphs": [],
                    "note": "",
                }
                current_section["subsections"].append(current_subsection)

        # PARAGRAPH
        elif "paragraph" in classes:
            if current_subsection:
                para_text = get_text(el)

                if isinstance(current_subsection["paragraphs"], list):
                    current_subsection["paragraphs"].append(para_text)
                else:
                    if current_subsection["paragraphs"]:
                        current_subsection["paragraphs"] += " " + para_text
                    else:
                        current_subsection["paragraphs"] = para_text

        # NOTES
        elif "Pnote" in classes:
            target = current_subsection or current_section
            if target:
                target["note"] = el.get_text(strip=True)

    return {
        "act": act_title,
        "short_title": short_title,
        "chapter": chapter,
        "version_date": version_date,
        "currency_date": currency_date,
        "last_amended": last_amended,
        "regulations": regulations,
        "sections": sections,
    }


def scrape(url: str) -> dict:
    soup = fetch_soup_js(url, wait_for=".section")
    result = _parse(soup)
    if not result["sections"]:
        raise ValueError(f"No sections found at {url}")
    return result


def scrape_file(filepath: str) -> dict:
    with open(filepath, encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    result = _parse(soup)
    if not result["sections"]:
        raise ValueError(f"No sections extracted from file: {filepath}")
    return result