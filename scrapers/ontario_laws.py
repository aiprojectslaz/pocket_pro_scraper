"""
Scraper for Ontario e-Laws (ontario.ca/laws).

Parses the DOM class structure used by the Ontario e-Laws site:
  section > headnote / subsection > paragraph / Pnote

NOTE: The ontario.ca site requires JavaScript to render. This scraper works
correctly on the rendered DOM (e.g. a saved HTML file or via Playwright).
A plain requests fetch will return a JS-wall page with no sections.
"""

import re

from bs4 import BeautifulSoup
from .base import fetch_soup_js, get_text


def _first_text(soup: BeautifulSoup, selector: str, fallback_substr: str) -> str:
    """Try CSS selector first; fall back to first <p> containing fallback_substr."""
    el = soup.select_one(selector)
    if not el and fallback_substr:
        el = next(
            (p for p in soup.find_all("p") if fallback_substr in p.get_text()),
            None,
        )
    return el.get_text(strip=True) if el else ""


def _parse(soup: BeautifulSoup) -> dict:
    # Use the <title> tag — it's server-rendered and always has the correct act name.
    # Strip the " | ontario.ca" suffix the site appends.
    act_title = ""
    title_el = soup.select_one("title")
    if title_el:
        act_title = title_el.get_text(strip=True).split(" | ")[0].strip()

    short_title = _first_text(soup, "p.shorttitle", "")
    chapter     = _first_text(soup, "p.chapter",    "Chapter")

    # Bug fix: both dates live in ONE element, e.g.:
    # "Consolidation period:April 19, 2021 -e-Laws currency date(March 25, 2026)"
    # Use regex to extract just the bare date strings.
    combined_el = soup.select_one("p.DocVer") or next(
        (p for p in soup.find_all("p") if "Consolidation period" in p.get_text()), None
    )
    combined = combined_el.get_text(strip=True) if combined_el else ""
    m = re.search(r'Consolidation period[^A-Za-z]+([A-Za-z].*?)\s*-\s*e-Laws', combined)
    version_date = m.group(1).strip() if m else combined
    m2 = re.search(r'e-Laws currency date[^A-Za-z(]*\(?([A-Za-z].*?)\)?$', combined)
    currency_date = m2.group(1).strip() if m2 else ""

    # Bug fix: strip the "Last amendment:" label prefix, keep only the citation.
    last_amended_raw = _first_text(soup, "p.lastAmendDate", "Last amendment")
    last_amended = re.sub(r'^Last amendment\s*[:\s]+', '', last_amended_raw,
                          flags=re.IGNORECASE).strip()

    # Regulations: pair volume-label (reg number) with doc-row title.
    # Use CSS [class*=] substring selector — more reliable than exact class match.
    regulations = []
    reg_div = soup.select_one("div.reg-content")
    if reg_div:
        labels = reg_div.select('[class*="volume-label"]')
        titles  = reg_div.select('[class*="doc-row__title"]')
        for i, label_el in enumerate(labels):
            number = label_el.get_text(strip=True)
            title  = titles[i].get_text(strip=True) if i < len(titles) else ""
            if number or title:
                regulations.append({"number": number, "title": title})

    sections = []
    current_section = None
    current_subsection = None
    # Bug fix: headnotes in the Ontario e-Laws DOM are siblings that appear
    # BEFORE their section div, not children inside it.  Buffer the headnote
    # text and apply it when the next section element is created.
    pending_headnote = ""

    for el in soup.find_all(True):
        classes = el.get("class", [])

        if "section" in classes:
            bold = el.find("b")
            current_section = {
                "section_number": get_text(bold) if bold else "",
                "title": pending_headnote,   # apply buffered headnote
                "text": get_text(el),
                "subsections": [],
                "note": "",
            }
            pending_headnote = ""            # reset buffer
            current_subsection = None
            sections.append(current_section)

        elif "headnote" in classes:
            pending_headnote = el.get_text(strip=True)   # buffer for next section

        elif "subsection" in classes:
            if current_section:
                current_subsection = {
                    "text": get_text(el),
                    "paragraphs": [],
                    "note": "",
                }
                current_section["subsections"].append(current_subsection)

        elif "definition" in classes:
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
