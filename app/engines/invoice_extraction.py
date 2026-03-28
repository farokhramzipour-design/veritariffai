"""
Invoice PDF extraction engine.

Extracts structured fields from a trade invoice PDF using:
1. pypdf  – pulls embedded text from digitally-generated PDFs
2. OpenAI – interprets the raw text and returns a typed JSON payload
"""

from __future__ import annotations

import base64
import io
import json
import os
import re
from typing import Optional

from app.engines.base import EngineError

try:
    from pypdf import PdfReader  # type: ignore
except Exception:  # pragma: no cover
    PdfReader = None  # type: ignore

try:
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore

try:
    import openapi as openapi_pkg  # type: ignore
except Exception:  # pragma: no cover
    openapi_pkg = None  # type: ignore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_model() -> str:
    from app.config import settings  # local import to avoid circular
    return getattr(settings, "openai_model", None) or os.getenv("OPENAI_MODEL") or "gpt-4o"


def _ensure_key():
    if not os.getenv("OPENAI_API_KEY") and os.getenv("openapi_API_KEY"):
        os.environ["OPENAI_API_KEY"] = os.getenv("openapi_API_KEY") or ""


def _extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Return all embedded text from a PDF. Returns empty string for image-only PDFs."""
    if PdfReader is None:
        raise EngineError(
            code="PDF_LIBRARY_MISSING",
            message="pypdf is not installed. Add `pypdf>=4.0.0` to requirements.",
        )
    reader = PdfReader(io.BytesIO(pdf_bytes))
    pages_text: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        pages_text.append(text)
    return "\n".join(pages_text).strip()


# ---------------------------------------------------------------------------
# OpenAI prompt
# ---------------------------------------------------------------------------

INVOICE_SYSTEM_PROMPT = """
You are a trade & customs document specialist. You will receive the raw text
extracted from a commercial invoice PDF. Extract every field listed below and
return ONLY a valid JSON object — no markdown, no preamble, no explanation.

Set any field you cannot determine to null.

Rules:
- Dates: ISO 8601 format (YYYY-MM-DD).
- Countries: ISO 3166-1 alpha-2 codes (e.g. "GB", "CN", "DE").
- Monetary amounts: numeric only, no currency symbols.
- currency: "GBP", "EUR", or "USD". Infer from symbols: £=GBP, €=EUR, $=USD.
- incoterms: standard 3-letter code (EXW, FOB, CIF, DAP, DDP, …) or null.
- hs_code in line items: best 6–10 digit code you can identify; null if absent.
- weight_kg: convert to kg if another unit is stated; null if unknown.

Response format (JSON only):
{
  "invoice_number": "string or null",
  "invoice_date": "YYYY-MM-DD or null",
  "po_number": "string or null",

  "seller": {
    "name": "string or null",
    "address": "string or null",
    "country_code": "XX or null",
    "vat_number": "string or null",
    "eori_number": "string or null"
  },

  "buyer": {
    "name": "string or null",
    "address": "string or null",
    "country_code": "XX or null",
    "vat_number": "string or null",
    "eori_number": "string or null"
  },

  "origin_country": "XX or null",
  "destination_country": "XX or null",
  "incoterms": "string or null",
  "incoterms_place": "string or null",
  "currency": "string or null",
  "payment_terms": "string or null",

  "line_items": [
    {
      "line_number": integer or null,
      "description": "string",
      "hs_code": "string or null",
      "quantity": number or null,
      "unit": "string or null",
      "unit_price": number or null,
      "total_price": number or null,
      "weight_kg": number or null,
      "country_of_origin": "XX or null"
    }
  ],

  "subtotal": number or null,
  "freight_cost": number or null,
  "insurance_cost": number or null,
  "other_charges": number or null,
  "total_invoice_value": number or null,
  "total_weight_kg": number or null,

  "customs_notes": "string or null",
  "extraction_confidence": integer,
  "warnings": ["list of any caveats or assumptions made"]
}
"""


def _call_openai(raw_text: str) -> dict:
    _ensure_key()
    model = _get_model()

    user_content = (
        "Here is the raw text extracted from the commercial invoice PDF.\n"
        "Extract all invoice fields as instructed:\n\n"
        f"{raw_text[:15000]}"  # cap to avoid token overflow
    )

    if openapi_pkg and hasattr(openapi_pkg, "openapi"):
        client_obj = openapi_pkg.openapi()  # type: ignore
        message = client_obj.messages.create(
            model=model,
            max_tokens=2048,
            system=INVOICE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
        )
        raw_resp = message.content[0].text.strip()
    elif OpenAI is not None:
        client_obj = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        resp = client_obj.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": INVOICE_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=0.1,
            max_tokens=2048,
        )
        raw_resp = resp.choices[0].message.content.strip()  # type: ignore
    else:
        raise EngineError(
            code="AI_CLIENT_MISSING",
            message="No AI client available. Install 'openai' package.",
        )

    # Strip accidental markdown fences
    raw_resp = re.sub(r"^```(?:json)?\s*", "", raw_resp)
    raw_resp = re.sub(r"\s*```$", "", raw_resp)
    return json.loads(raw_resp)


# ---------------------------------------------------------------------------
# Public engine entry-point
# ---------------------------------------------------------------------------

def extract_invoice_fields(pdf_bytes: bytes, filename: str = "invoice.pdf") -> dict:
    """
    Parse a PDF invoice and return structured customs-relevant fields.

    Args:
        pdf_bytes: Raw bytes of the uploaded PDF file.
        filename:  Original filename (for logging / warnings).

    Returns:
        dict with extracted fields + meta.

    Raises:
        EngineError: on unrecoverable parsing failures.
    """
    # Step 1 – pull embedded text
    try:
        raw_text = _extract_text_from_pdf(pdf_bytes)
    except EngineError:
        raise
    except Exception as exc:
        raise EngineError(
            code="PDF_PARSE_ERROR",
            message=f"Failed to read PDF: {exc}",
        ) from exc

    warnings: list[str] = []
    if len(raw_text) < 50:
        warnings.append(
            "Very little text could be extracted from this PDF. "
            "It may be a scanned/image-based document; results may be incomplete."
        )

    # Step 2 – call OpenAI for structured extraction
    try:
        extracted = _call_openai(raw_text if raw_text else f"[PDF filename: {filename}]")
    except EngineError:
        raise
    except json.JSONDecodeError as exc:
        raise EngineError(
            code="AI_PARSE_ERROR",
            message=f"AI returned non-JSON response: {exc}",
        ) from exc
    except Exception as exc:
        raise EngineError(
            code="AI_ERROR",
            message=f"OpenAI extraction failed: {exc}",
        ) from exc

    # Merge engine-level warnings with AI warnings
    ai_warnings = extracted.pop("warnings", []) or []
    extracted["warnings"] = warnings + ai_warnings
    extracted["source_filename"] = filename
    extracted["raw_text_chars"] = len(raw_text)

    return extracted
