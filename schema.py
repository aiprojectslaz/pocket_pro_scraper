from pydantic import BaseModel


class Subsection(BaseModel):
    text: str
    paragraphs: list[str]
    note: str = ""


class Section(BaseModel):
    section_number: str
    title: str = ""
    text: str = ""
    subsections: list[Subsection]
    note: str = ""


class Regulation(BaseModel):
    number: str = ""   # e.g. "O. Reg. 261/13"
    title:  str = ""   # e.g. "DESIGNATED DISEASES"


class Act(BaseModel):
    act: str
    short_title:   str = ""
    chapter:       str = ""
    version_date:  str = ""   # "Consolidation period: April 19, 2021"
    currency_date: str = ""   # "e-Laws currency date (March 25, 2026)"
    last_amended:  str = ""
    regulations:   list[Regulation] = []
    sections:      list[Section]


class SourceDocument(BaseModel):
    """
    Staging record written by the scraper.
    Maps to core.source_documents in Supabase.
    Human or automation later promotes these into core.procedures.
    """
    title: str
    source_url: str = ""
    source_type: str          # "html" | "pdf" | "xml"
    domain: str = ""
    content: dict             # full Act (or Claude-structured) dict
