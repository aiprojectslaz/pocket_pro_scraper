import pdfplumber

MAX_CHARS = 100_000


def scrape_pdf(filepath: str) -> str:
    with pdfplumber.open(filepath) as pdf:
        pages_text = []
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages_text.append(text)

    if not pages_text:
        raise ValueError(f"No text extracted from PDF: {filepath}")

    full_text = "\n".join(pages_text)

    if len(full_text) > MAX_CHARS:
        print(f"[pdf_scraper] Warning: text truncated from {len(full_text)} to {MAX_CHARS} chars")
        full_text = full_text[:MAX_CHARS]

    return full_text
