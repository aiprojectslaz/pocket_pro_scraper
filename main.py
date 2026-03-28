import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from scrapers import scrape_html, scrape_html_file, scrape_pdf, scrape_xml
from structurer import structure_text
from importer import import_procedure

OUTPUT_DIR = Path("output")


def save_output(data: dict, label: str) -> Path:
    OUTPUT_DIR.mkdir(exist_ok=True)
    safe_label = "".join(c if c.isalnum() or c in "-_" else "_" for c in label)
    out_path = OUTPUT_DIR / f"{safe_label}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return out_path


def process(raw_text: str, label: str, dry_run: bool) -> None:
    print(f"[structurer] Sending {len(raw_text)} chars to Claude ({label})...")
    structured = structure_text(raw_text)

    out_path = save_output(structured, label)
    print(f"[output] Saved to {out_path}")

    if dry_run:
        print("[dry-run] JSON output:")
        print(json.dumps(structured, indent=2, ensure_ascii=False))
        print("[dry-run] Skipping Supabase import.")
    else:
        print("[importer] Validating and inserting into Supabase...")
        result = import_procedure(structured)
        print(f"[importer] Inserted record: {result}")


def run_single(args: argparse.Namespace) -> None:
    source = args.source

    if source == "html":
        print(f"[scraper] Fetching HTML from {args.url}")
        raw = scrape_html(args.url)
        label = (raw.get("act", "") or args.url.rstrip("/").split("/")[-1] or "html_page")
    elif source == "pdf":
        print(f"[scraper] Extracting PDF text from {args.file}")
        raw = scrape_pdf(args.file)
        label = Path(args.file).stem
    elif source == "xml":
        print(f"[scraper] Parsing XML from {args.file}")
        raw = scrape_xml(args.file, section_id=args.section)
        label = Path(args.file).stem + (f"_{args.section}" if args.section else "")
    else:
        print(f"Unknown source: {source}", file=sys.stderr)
        sys.exit(1)

    process(raw, label, dry_run=args.dry_run)


def run_batch(args: argparse.Namespace) -> None:
    sources_root = Path("sources")
    tasks: list[tuple[str, str, str]] = []

    for html_file in sorted((sources_root / "html").glob("*.html")):
        tasks.append(("html_file", str(html_file), html_file.stem))

    for pdf_file in sorted((sources_root / "pdf").glob("*.pdf")):
        tasks.append(("pdf", str(pdf_file), pdf_file.stem))

    for xml_file in sorted((sources_root / "xml").glob("*.xml")):
        tasks.append(("xml", str(xml_file), xml_file.stem))

    if not tasks:
        print("[batch] No source files found in sources/ subdirectories.")
        return

    print(f"[batch] Found {len(tasks)} file(s) to process.")
    errors: list[tuple[str, str]] = []

    for source_type, filepath, label in tasks:
        print(f"\n[batch] Processing: {filepath}")
        try:
            if source_type == "html_file":
                raw = scrape_html_file(filepath)
            elif source_type == "pdf":
                raw = scrape_pdf(filepath)
            elif source_type == "xml":
                raw = scrape_xml(filepath)
            else:
                raise ValueError(f"Unknown source type: {source_type}")
            process(raw, label, dry_run=args.dry_run)
        except Exception as e:
            print(f"[batch] ERROR processing {filepath}: {e}", file=sys.stderr)
            errors.append((filepath, str(e)))

    success_count = len(tasks) - len(errors)
    print(f"\n[batch] Done. {success_count} succeeded, {len(errors)} failed.")
    if errors:
        for path, err in errors:
            print(f"  FAILED: {path} — {err}", file=sys.stderr)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="pocket-procedures-scraper: extract and structure government procedure documents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --source html --url https://laws-lois.justice.gc.ca/eng/acts/C-46/section-494.html --dry-run
  python main.py --source pdf --file sources/pdf/procedure.pdf --dry-run
  python main.py --source xml --file sources/xml/statute.xml --section s-12 --dry-run
  python main.py --batch --dry-run
        """,
    )
    parser.add_argument(
        "--source",
        choices=["html", "pdf", "xml"],
        help="Source type for single-file mode",
    )
    parser.add_argument("--url", help="URL to fetch (use with --source html)")
    parser.add_argument("--file", help="File path (use with --source pdf or xml)")
    parser.add_argument(
        "--section", help="XML section id to extract (use with --source xml)"
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Process all files in sources/ subdirectories automatically",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print JSON and save to output/ but skip Supabase import",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.batch:
        run_batch(args)
    elif args.source:
        if args.source == "html" and not args.url:
            parser.error("--source html requires --url")
        if args.source in ("pdf", "xml") and not args.file:
            parser.error(f"--source {args.source} requires --file")
        run_single(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAborted.", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)
