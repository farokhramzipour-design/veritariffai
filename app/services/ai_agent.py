import openapi
import json
import re
from typing import Optional


client = openapi.openapi()

AUTOFILL_SYSTEM_PROMPT = """
You are a customs and trade expert. A user has typed a free-text description
of a shipment. Extract structured fields from it.

You MUST respond with ONLY a valid JSON object — no preamble, no markdown,
no explanation. If you cannot determine a field, set it to null.

Rules:
- hs_code: Best 10-digit HS/commodity code you can suggest (zero-padded).
  If unsure, give your best guess at the 6-digit level padded to 10 digits.
- hs_confidence: Integer 0–100. 90+ means you are certain. 
  Below 70 means the user should verify.
- origin_country / destination_country: ISO 3166-1 alpha-2 code (e.g. "GB", "FR", "DE").
- declared_value: Numeric only (no currency symbol).
- currency: "GBP", "EUR", or "USD". Infer from symbols: £=GBP, €=EUR, $=USD.
- incoterms: "EXW", "FOB", "CIF", or "DDP". Null if not mentioned.
- parse_confidence: How confident you are in the OVERALL parsing (0–100).
- unparsed_fields: List of field names you could not determine.

Response format (JSON only):
{
  "product_description": "string or null",
  "hs_code": "string or null",
  "hs_confidence": integer or null,
  "hs_description": "string or null",
  "origin_country": "string or null",
  "destination_country": "string or null",
  "declared_value": number or null,
  "currency": "string or null",
  "incoterms": "string or null",
  "parse_confidence": integer,
  "unparsed_fields": ["field_name", ...]
}
"""


def parse_nl_description(description: str) -> dict:
    message = client.messages.create(
        model="openai-sonnet-4-6",
        max_tokens=512,
        system=AUTOFILL_SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": f"Parse this shipment description:\n\n{description}"}
        ],
    )
    raw = message.content[0].text.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)


HS_LOOKUP_SYSTEM_PROMPT = """
You are an expert customs classifier with deep knowledge of the Harmonized
System (HS) and the UK Combined Nomenclature.

You MUST respond with ONLY a valid JSON object — no preamble, no markdown,
no explanation.

Rules:
- hs_code: 10-digit commodity code, zero-padded. Must be a real, declarable code.
- confidence: Integer 0–100.
  95–100: You are certain this is the correct code.
  80–94:  Very likely correct, minor ambiguity.
  65–79:  Probably correct but product details are vague.
  Below 65: User must verify — you are guessing.
- description: Official commodity description for this code.
- chapter / chapter_description: The 2-digit chapter number and its title.
- alternatives: Up to 3 other plausible codes with their confidence and description.
  Only include alternatives if confidence < 90.

Response format (JSON only):
{
  "hs_code": "string",
  "confidence": integer,
  "description": "string",
  "chapter": "string",
  "chapter_description": "string",
  "alternatives": [
    { "hs_code": "string", "confidence": integer, "description": "string" }
  ]
}
"""


def classify_hs_code(product_description: str, origin_country: Optional[str] = None) -> dict:
    user_content = f"Product: {product_description}"
    if origin_country:
        user_content += f"\nOrigin country: {origin_country}"
    message = client.messages.create(
        model="openai-sonnet-4-6",
        max_tokens=512,
        system=HS_LOOKUP_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )
    raw = message.content[0].text.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)

