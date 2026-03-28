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


class Act(BaseModel):
    act: str
    sections: list[Section]


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
