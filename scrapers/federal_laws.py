"""
Scraper for the Federal Justice Canada laws site (laws-lois.justice.gc.ca).

The site serves static HTML — no JavaScript rendering required.

DOM structure used by Justice Canada:
  .Section           → top-level section block
  .MarginalNote      → section heading / marginal note
  .Subsection        → numbered subsection (1), (2)...
  .Paragraph         → lettered paragraph (a), (b)...
  .HistoricalNote    → editorial/historical note (treated as Pnote)
"""

from bs4 import BeautifulSoup
from .base import fetch_soup, get_text


def _parse(soup: BeautifulSoup) -> dict:
    # Act title — try the page <h1> or the breadcrumb link for the Act
    act_title = ""
    for selector in ["h1", ".Title-of-Act", ".act-title", "title"]:
        el = soup.select_one(selector)
        if el:
            act_title = el.get_text(strip=True)
            break

    sections = []
    current_section = None
    current_subsection = None

    # Justice Canada wraps each section in a <div class="Section"> or
    # uses the HTML5 <section> element with a class containing "Section".
    for el in soup.find_all(True):
        classes = el.get("class", [])
        tag = el.name

        # ── Section boundary ────────────────────────────────────────────
        if "Section" in classes or (tag == "section" and classes):
            # The section number is usually inside a <span class="lawlabel">
            # or the first bold/strong child.
            label_el = el.select_one(".lawlabel, b, strong")
            current_section = {
                "section_number": label_el.get_text(strip=True) if label_el else "",
                "title": "",
                "text": get_text(el),
                "subsections": [],
                "note": "",
            }
            current_subsection = None
            sections.append(current_section)

        # ── Marginal note → section title ───────────────────────────────
        elif "MarginalNote" in classes:
            if current_section:
                current_section["title"] = el.get_text(strip=True)

        # ── Subsection ──────────────────────────────────────────────────
        elif "Subsection" in classes:
            if current_section:
                current_subsection = {
                    "text": get_text(el),
                    "paragraphs": [],
                    "note": "",
                }
                current_section["subsections"].append(current_subsection)

        # ── Paragraph (a), (b)... ───────────────────────────────────────
        elif "Paragraph" in classes:
            if current_subsection:
                current_subsection["paragraphs"].append(get_text(el))
            elif current_section:
                # Paragraph directly under a section (no subsection wrapper)
                if not current_section["subsections"]:
                    current_subsection = {
                        "text": "",
                        "paragraphs": [],
                        "note": "",
                    }
                    current_section["subsections"].append(current_subsection)
                current_subsection["paragraphs"].append(get_text(el))

        # ── Historical / editorial note ─────────────────────────────────
        elif "HistoricalNote" in classes or "Note" in classes:
            target = current_subsection or current_section
            if target:
                target["note"] = el.get_text(strip=True)

    return {"act": act_title, "sections": sections}


def scrape(url: str) -> dict:
    soup = fetch_soup(url)
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
