import os

from dotenv import load_dotenv
from pydantic import ValidationError
from supabase import Client, create_client

from schema import Procedure

load_dotenv()

TABLE_NAME = "procedures"


def get_supabase_client() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url:
        raise KeyError("SUPABASE_URL environment variable is not set")
    if not key:
        raise KeyError("SUPABASE_KEY environment variable is not set")
    return create_client(url, key)


def import_procedure(data: dict) -> dict:
    try:
        procedure = Procedure(**data)
    except ValidationError as e:
        raise ValueError(f"Schema validation failed:\n{e}") from e

    client = get_supabase_client()
    serialized = procedure.model_dump()

    response = client.table(TABLE_NAME).insert(serialized).execute()

    if not response.data:
        raise RuntimeError(
            f"Supabase insert returned no data. Response: {response}"
        )

    return response.data[0]
