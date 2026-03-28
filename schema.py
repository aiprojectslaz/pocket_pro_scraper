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
