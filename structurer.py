import json
import os
import re

import anthropic
from dotenv import load_dotenv

load_dotenv()

MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 4096

SYSTEM_PROMPT = """\
You are a document structuring assistant. You will be given raw text extracted from a \
government statute or legislation document. Your task is to extract and return structured \
data as valid JSON — nothing else. Do not include any explanation, markdown fences, or \
extra text.

Return a single JSON object matching this exact schema:
{
  "act": "string — the full title of the Act",
  "sections": [
    {
      "section_number": "string — e.g. '1', '2(1)', '494'",
      "title": "string — section heading/marginal note if present, else empty string",
      "text": "string — introductory text of the section before subsections, or full text if no subsections",
      "subsections": [
        {
          "text": "string — full text of this subsection",
          "paragraphs": ["string — each lettered paragraph (a), (b)... as a separate item"],
          "note": "string — any marginal or editorial note attached to this subsection, else empty string"
        }
      ],
      "note": "string — any marginal or editorial note at the section level, else empty string"
    }
  ]
}

Rules:
- All fields are required. Use empty strings or empty arrays if information is not present.
- Extract every section found in the document in order.
- Paragraphs are the lettered sub-items within a subsection, e.g. (a), (b), (c).
- Return only the JSON object. No markdown, no commentary.
"""


def structure_text(raw: str | dict) -> dict:
    # HTML scraper already returns structured data — pass through without calling Claude
    if isinstance(raw, dict):
        return raw

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise KeyError("ANTHROPIC_API_KEY environment variable is not set")

    client = anthropic.Anthropic(api_key=api_key)

    message = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": f"Document text:\n\n{raw}"}
        ],
    )

    raw_response = message.content[0].text.strip()

    # Strip markdown code fences if present
    raw_response = re.sub(r"^```(?:json)?\s*", "", raw_response)
    raw_response = re.sub(r"\s*```$", "", raw_response)

    # Extract the first JSON object in case there is surrounding text
    match = re.search(r"\{.*\}", raw_response, re.DOTALL)
    if not match:
        raise ValueError(
            f"No JSON object found in Claude response. Response was:\n{raw_response[:500]}"
        )

    try:
        return json.loads(match.group())
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Failed to parse JSON from Claude response: {e}\n"
            f"Response excerpt:\n{raw_response[:500]}"
        ) from e
