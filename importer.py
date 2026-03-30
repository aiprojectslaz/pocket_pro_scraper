import os
import requests
from urllib.parse import urlparse

from dotenv import load_dotenv
from pydantic import ValidationError

from schema import SourceDocument

load_dotenv()

TARGET_SCHEMA = "core"
TARGET_TABLE  = "source_documents"


def _supabase_creds() -> tuple[str, dict]:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url:
        raise KeyError("SUPABASE_URL environment variable is not set")
    if not key:
        raise KeyError("SUPABASE_KEY environment variable is not set")
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Content-Profile": TARGET_SCHEMA,
        "Accept-Profile": TARGET_SCHEMA,
        "Prefer": "return=representation",
    }
    return url, headers


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

    supabase_url, headers = _supabase_creds()
    endpoint = f"{supabase_url}/rest/v1/{TARGET_TABLE}"
    response = requests.post(endpoint, headers=headers, json=validated.model_dump())

    if not response.ok:
        raise RuntimeError(
            f"Supabase insert failed ({response.status_code}): {response.text}"
        )

    rows = response.json()
    return rows[0] if isinstance(rows, list) else rows
