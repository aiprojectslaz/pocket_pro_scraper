# pocket-procedures-scraper

Scrapes government procedure documents (HTML pages, PDFs, Justice Canada XML) and uses the Claude API to extract structured JSON data, then optionally inserts the results into a Supabase database.

## Project Structure

```
pocket-procedures-scraper/
├── main.py                  # CLI entry point
├── schema.py                # Pydantic model for procedure data
├── structurer.py            # Claude API integration
├── importer.py              # Supabase insertion
├── scrapers/
│   ├── __init__.py
│   ├── html_scraper.py      # requests + BeautifulSoup4
│   ├── pdf_scraper.py       # pdfplumber
│   └── xml_scraper.py       # lxml (Justice Canada XML format)
├── sources/
│   ├── html/                # Place local .html files here for --batch
│   ├── pdf/                 # Place .pdf files here for --batch or --source pdf
│   └── xml/                 # Place .xml files here for --batch or --source xml
├── output/                  # Structured JSON output files (auto-created)
├── requirements.txt
├── .env.example
└── README.md
```

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in your keys:

```
ANTHROPIC_API_KEY=your_anthropic_api_key_here
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your_supabase_anon_or_service_key_here
```

### 3. Supabase table setup

Create a `procedures` table in your Supabase project with these columns:

| Column             | Type   |
|--------------------|--------|
| `procedure_name`   | text   |
| `procedure_number` | text   |
| `procedure_chapter`| text   |
| `rationale`        | text   |
| `roles`            | jsonb  |
| `sub_procedures`   | jsonb  |
| `definitions`      | jsonb  |

---

## Usage

### Fetch from a URL (HTML)

```bash
python main.py --source html --url https://laws-lois.justice.gc.ca/eng/acts/C-46/section-494.html
```

With `--dry-run` (prints JSON, saves to `output/`, skips Supabase):

```bash
python main.py --source html \
  --url https://laws-lois.justice.gc.ca/eng/acts/C-46/section-494.html \
  --dry-run
```

### Extract from a PDF

```bash
python main.py --source pdf --file sources/pdf/procedure-001.pdf --dry-run
```

### Parse a Justice Canada XML file

Parse the full document:

```bash
python main.py --source xml --file sources/xml/statute.xml --dry-run
```

Parse a specific section by `id` attribute:

```bash
python main.py --source xml --file sources/xml/statute.xml --section s-12 --dry-run
```

### Batch mode

Process all files found in `sources/html/`, `sources/pdf/`, and `sources/xml/` automatically:

```bash
python main.py --batch --dry-run
```

Files are discovered by extension (`.html`, `.pdf`, `.xml`) and processed in alphabetical order per directory. Errors in individual files are logged but do not stop the batch.

---

## Output

Structured JSON files are saved to `output/<filename>.json` after every successful extraction, regardless of `--dry-run` mode.

Example output structure:

```json
{
  "procedure_name": "Arrest Without Warrant",
  "procedure_number": "494",
  "procedure_chapter": "Criminal Code",
  "rationale": "Authorises citizens and peace officers to arrest without warrant...",
  "roles": [
    {
      "role_title": "Peace Officer",
      "steps": [
        "Find a person committing an indictable offence",
        "Believe on reasonable grounds the person has committed an offence"
      ]
    }
  ],
  "sub_procedures": [],
  "definitions": [
    {
      "term": "peace officer",
      "definition": "A person employed for the preservation and maintenance of public peace"
    }
  ]
}
```

---

## Dry Run vs Live Mode

| Mode | Behaviour |
|------|-----------|
| `--dry-run` | Prints JSON to console, saves to `output/`, skips Supabase insert |
| *(no flag)* | Saves to `output/` **and** inserts into Supabase `procedures` table |

---

## Sample Test

```bash
python main.py --source html \
  --url https://laws-lois.justice.gc.ca/eng/acts/C-46/section-494.html \
  --dry-run
```
