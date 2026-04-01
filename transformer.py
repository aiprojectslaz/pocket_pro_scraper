"""
Transform raw.source_documents → core.acts / core.sections.

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


def _headers(key: str, schema: str, on_conflict: str = "return=representation") -> dict:
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Content-Profile": schema,
        "Accept-Profile": schema,
        "Prefer": on_conflict,
    }


def _get(base_url: str, key: str, schema: str, table: str, params: dict | None = None) -> list:
    r = requests.get(
        f"{base_url}/rest/v1/{table}",
        headers=_headers(key, schema),
        params=params,
    )
    r.raise_for_status()
    return r.json()


def _post(base_url: str, key: str, schema: str, table: str, data: dict, ignore_duplicates: bool = False) -> dict | None:
    prefer = "resolution=ignore-duplicates,return=representation" if ignore_duplicates else "return=representation"
    r = requests.post(
        f"{base_url}/rest/v1/{table}",
        headers=_headers(key, schema, prefer),
        json=data,
    )
    if not r.ok:
        raise RuntimeError(f"POST {schema}.{table} failed ({r.status_code}): {r.text}")
    rows = r.json()
    if not rows:
        return None  # duplicate was ignored
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
# Section type inference
# ---------------------------------------------------------------------------

_SECTION_TYPE_KEYWORDS: list[tuple[str, str]] = [
    ("definitions", "definitions"),
    ("purpose", "purpose"),
    ("power", "powers"),
    ("offence", "offences"),
    ("penalty", "offences"),
    ("procedure", "procedure"),
    ("process", "procedure"),
    ("application", "procedure"),
]


def _infer_section_type(heading: str, section_num: str) -> str:
    heading_lower = heading.lower()
    for keyword, section_type in _SECTION_TYPE_KEYWORDS:
        if keyword in heading_lower:
            return section_type
    if section_num in ("1", "1."):
        return "definitions"
    return "general"


# ---------------------------------------------------------------------------
# Transform logic
# ---------------------------------------------------------------------------

def transform_document(raw_row: dict, base_url: str, key: str, dry_run: bool) -> None:
    content  = raw_row.get("content", {})
    raw_id   = raw_row["id"]
    sections = content.get("sections", [])

    if dry_run:
        print(f"  [dry-run] act:         {content.get('act', '')}")
        print(f"  [dry-run] chapter:     {content.get('chapter', '')}")
        print(f"  [dry-run] jurisdiction: ontario")
        print(f"  [dry-run] sections:    {len(sections)}")
        return

    # 1. Insert into core.acts (ignore if same source_url already exists)
    act = _post(base_url, key, "core", "acts", {
        "title":        content.get("act", ""),
        "jurisdiction": "ontario",
        "content_tier": "free",
        "source_url":   raw_row.get("source_url", ""),
        "chapter":      content.get("chapter", ""),
        "short_title":  content.get("short_title", ""),
        "version_date": content.get("version_date", ""),
        "currency_date": content.get("currency_date", ""),
        "last_amended": content.get("last_amended", ""),
    }, ignore_duplicates=True)

    if act is None:
        print(f"  [transform] core.acts: duplicate source_url — skipping (already imported)")
        return

    act_id = act["id"]
    print(f"  [transform] core.acts id={act_id}: {act['title']}")

    # 2. Insert into core.sections
    section_count = 0
    for section in sections:
        heading = section.get("title", "")
        section_num = section.get("section_number", "")
        section_type = _infer_section_type(heading, section_num)
        _post(base_url, key, "core", "sections", {
            "act_id":       act_id,
            "section_num":  section_num,
            "heading":      heading,
            "raw_text":     section.get("text", ""),
            "section_type": section_type,
            "promoted":     False,
        }, ignore_duplicates=True)
        section_count += 1

    print(f"  [transform] {section_count} sections inserted")

    # 3. Mark raw row as imported
    _patch(base_url, key, "raw", "source_documents", raw_id, {"status": "imported"})
    print(f"  [transform] raw id={raw_id} marked as imported")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Transform raw.source_documents into core.acts/sections"
    )
    parser.add_argument("--id",      type=int, help="Process one raw document by id")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    args = parser.parse_args()

    base_url, key = _creds()

    if args.id:
        rows = _get(base_url, key, "raw", "source_documents", {
            "id":        f"eq.{args.id}",
            "confirmed": "eq.true",
            "status":    "eq.pending",
        })
    else:
        rows = _get(base_url, key, "raw", "source_documents", {
            "status":    "eq.pending",
            "confirmed": "eq.true",
        })

    if not rows:
        if args.id:
            print(f"[transform] id={args.id} not found, already imported, or confirmed=false — skipping.")
        else:
            print("[transform] No confirmed pending documents found.")
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
