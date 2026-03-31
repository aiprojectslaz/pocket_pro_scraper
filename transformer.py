"""
Transform raw.source_documents → core.acts / core.sections / core.definitions.

Usage:
  python transformer.py              # process all pending rows in raw.source_documents
  python transformer.py --id 42      # process one specific raw document by id
  python transformer.py --dry-run    # preview without writing anything
"""

import argparse
import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()


# ---------------------------------------------------------------------------
# Supabase REST helpers
# ---------------------------------------------------------------------------

def _creds() -> tuple[str, str]:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url:
        raise KeyError("SUPABASE_URL is not set in .env")
    if not key:
        raise KeyError("SUPABASE_KEY is not set in .env")
    return url, key


def _headers(key: str, schema: str) -> dict:
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Content-Profile": schema,
        "Accept-Profile": schema,
        "Prefer": "return=representation",
    }


def _get(base_url: str, key: str, schema: str, table: str, params: dict | None = None) -> list:
    r = requests.get(
        f"{base_url}/rest/v1/{table}",
        headers=_headers(key, schema),
        params=params,
    )
    r.raise_for_status()
    return r.json()


def _post(base_url: str, key: str, schema: str, table: str, data: dict) -> dict:
    r = requests.post(
        f"{base_url}/rest/v1/{table}",
        headers=_headers(key, schema),
        json=data,
    )
    if not r.ok:
        raise RuntimeError(f"POST {schema}.{table} failed ({r.status_code}): {r.text}")
    rows = r.json()
    return rows[0] if isinstance(rows, list) else rows


def _patch(base_url: str, key: str, schema: str, table: str, row_id: int, data: dict) -> None:
    h = _headers(key, schema)
    h["Prefer"] = "return=minimal"
    r = requests.patch(
        f"{base_url}/rest/v1/{table}?id=eq.{row_id}",
        headers=h,
        json=data,
    )
    if not r.ok:
        raise RuntimeError(f"PATCH {schema}.{table} failed ({r.status_code}): {r.text}")


# ---------------------------------------------------------------------------
# Transform logic
# ---------------------------------------------------------------------------

def _definition_text(sub: dict) -> str:
    """Extract definition text from a subsection dict (handles list or string)."""
    paragraphs = sub.get("paragraphs", [])
    if isinstance(paragraphs, list):
        return paragraphs[0].strip() if paragraphs else ""
    return str(paragraphs).strip()


def transform_document(raw_row: dict, base_url: str, key: str, dry_run: bool) -> None:
    content   = raw_row.get("content", {})
    raw_id    = raw_row["id"]
    sections  = content.get("sections", [])
    def_count = sum(
        len(s.get("subsections", []))
        for s in sections
        if s.get("title", "").lower() == "definitions"
    )

    if dry_run:
        print(f"  [dry-run] act:         {content.get('act', '')}")
        print(f"  [dry-run] chapter:     {content.get('chapter', '')}")
        print(f"  [dry-run] sections:    {len(sections)}")
        print(f"  [dry-run] definitions: {def_count}")
        return

    # 1. Insert act
    act = _post(base_url, key, "core", "acts", {
        "title":      content.get("act", ""),
        "chapter":    content.get("chapter", ""),
        "source_url": raw_row.get("source_url", ""),
    })
    act_id = act["id"]
    print(f"  [transform] act id={act_id}: {act['title']}")

    # 2. Insert sections + definitions
    for section in sections:
        _post(base_url, key, "core", "sections", {
            "act_id":         act_id,
            "section_number": section.get("section_number", ""),
            "title":          section.get("title", ""),
            "text":           section.get("text", ""),
        })

        if section.get("title", "").lower() == "definitions":
            for sub in section.get("subsections", []):
                _post(base_url, key, "core", "definitions", {
                    "act_id":     act_id,
                    "term":       sub.get("text", "").strip(),
                    "definition": _definition_text(sub),
                    "translation": sub.get("translation", ""),
                })

    print(f"  [transform] {len(sections)} sections, {def_count} definitions inserted")

    # 3. Mark raw row as imported
    _patch(base_url, key, "raw", "source_documents", raw_id, {"status": "imported"})
    print(f"  [transform] raw id={raw_id} marked as imported")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Transform raw.source_documents into core.acts/sections/definitions"
    )
    parser.add_argument("--id",      type=int, help="Process one raw document by id")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    args = parser.parse_args()

    base_url, key = _creds()

    if args.id:
        rows = _get(base_url, key, "raw", "source_documents", {"id": f"eq.{args.id}"})
    else:
        rows = _get(base_url, key, "raw", "source_documents", {"status": "eq.pending"})

    if not rows:
        print("[transform] No pending documents found.")
        return

    print(f"[transform] {len(rows)} document(s) to process.")
    errors: list[tuple[int, str]] = []

    for row in rows:
        print(f"\n[transform] id={row['id']} — {row.get('title', '(no title)')}")
        try:
            transform_document(row, base_url, key, dry_run=args.dry_run)
        except Exception as e:
            print(f"  ERROR: {e}", file=sys.stderr)
            errors.append((row["id"], str(e)))

    ok = len(rows) - len(errors)
    print(f"\n[transform] Done. {ok} succeeded, {len(errors)} failed.")
    if errors:
        for row_id, err in errors:
            print(f"  FAILED id={row_id}: {err}", file=sys.stderr)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAborted.", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)
