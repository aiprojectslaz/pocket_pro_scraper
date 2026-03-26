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
government procedure document. Your task is to extract and return structured data as \
valid JSON — nothing else. Do not include any explanation, markdown fences, or extra text.

Return a single JSON object matching this exact schema:
{
  "procedure_name": "string",
  "procedure_number": "string",
  "procedure_chapter": "string",
  "rationale": "string",
  "roles": [
    {
      "role_title": "string",
      "steps": ["string"]
    }
  ],
  "sub_procedures": [
    {
      "title": "string",
      "content": "string"
    }
  ],
  "definitions": [
    {
      "term": "string",
      "definition": "string"
    }
  ]
}

Rules:
- All fields are required. Use empty strings or empty arrays if information is not present.
- Extract as much detail as possible from the source text.
- Each role's steps should be individual action sentences in the order they appear.
- Sub-procedures are named sections describing a subordinate process.
- Definitions come from any glossary or definitions section in the document.
- Return only the JSON object. No markdown, no commentary.
"""


def structure_text(raw_text: str) -> dict:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise KeyError("ANTHROPIC_API_KEY environment variable is not set")

    client = anthropic.Anthropic(api_key=api_key)

    message = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": f"Document text:\n\n{raw_text}"}
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
