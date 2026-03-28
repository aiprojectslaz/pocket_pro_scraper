import os
from urllib.parse import urlparse

from dotenv import load_dotenv
from pydantic import ValidationError
from supabase import Client, create_client

from schema import SourceDocument

load_dotenv()

TARGET_SCHEMA = "core"
TARGET_TABLE  = "source_documents"


def get_supabase_client() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url:
        raise KeyError("SUPABASE_URL environment variable is not set")
    if not key:
        raise KeyError("SUPABASE_KEY environment variable is not set")
    return create_client(url, key)


def _extract_domain(url: str) -> str:
    return urlparse(url).netloc.replace("www.", "") if url else ""


def import_procedure(data: dict, source_url: str = "", source_type: str = "html") -> dict:
    doc = SourceDocument(
        title=data.get("act", data.get("procedure_name", "")),
        source_url=source_url,
        source_type=source_type,
        domain=_extract_domain(source_url),
        content=data,
    )

    try:
        validated = doc.model_validate(doc.model_dump())
    except ValidationError as e:
        raise ValueError(f"Schema validation failed:\n{e}") from e

    client = get_supabase_client()
    response = (
        client.schema(TARGET_SCHEMA)
        .table(TARGET_TABLE)
        .insert(validated.model_dump())
        .execute()
    )

    if not response.data:
        raise RuntimeError(
            f"Supabase insert returned no data. Response: {response}"
        )

    return response.data[0]
