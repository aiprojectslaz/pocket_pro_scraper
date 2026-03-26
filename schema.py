from pydantic import BaseModel


class Role(BaseModel):
    role_title: str
    steps: list[str]


class SubProcedure(BaseModel):
    title: str
    content: str


class Definition(BaseModel):
    term: str
    definition: str


class Procedure(BaseModel):
    procedure_name: str
    procedure_number: str
    procedure_chapter: str
    rationale: str
    roles: list[Role]
    sub_procedures: list[SubProcedure]
    definitions: list[Definition]
