"""
Mill Test Certificate (MTC) extraction engine.

Extracts steel-specific fields from an MTC PDF (EN 10204 3.1 / 3.2) using OpenAI:
  - Melt country + pour country (TCA mandatory)
  - Heat number (traceability)
  - Production route (BF-BOF / EAF / DRI-EAF) — needed for CBAM SEE
  - Chemical composition (Cr, Mo, C, Mn, Si, Ni, P, S, V, ...)
  - Mechanical properties (tensile, yield, elongation)
  - Issue date
  - Steel grade / standard
  - Certificate number
"""

from __future__ import annotations

import json
import logging
from io import BytesIO
from typing import Any

logger = logging.getLogger(__name__)


def extract_mtc_fields(
    *,
    pdf_bytes: bytes,
    filename: str = "mtc.pdf",
) -> dict[str, Any]:
    """
    Extract MTC fields from a PDF using pypdf (text) + OpenAI (structured parse).

    Returns a dict with fields and per-field confidence scores (0.0–1.0).
    """
    try:
        import pypdf  # type: ignore
    except ImportError:
        raise RuntimeError("pypdf is required for MTC extraction. Install it: pip install pypdf")

    # ── Extract text from PDF ──────────────────────────────────────────────
    try:
        reader = pypdf.PdfReader(BytesIO(pdf_bytes))
        pages_text = []
        for page in reader.pages:
            text = page.extract_text() or ""
            if text.strip():
                pages_text.append(text)
        raw_text = "\n".join(pages_text)
    except Exception as exc:
        logger.error("MTC PDF text extraction failed for %s: %s", filename, exc)
        raw_text = ""

    if not raw_text.strip():
        logger.warning("MTC %s: no extractable text — may be a scanned image", filename)

    # ── Call OpenAI for structured extraction ──────────────────────────────
    try:
        import openai  # type: ignore
        from app.config import settings

        client = openai.OpenAI(api_key=settings.openai_api_key)

        system_prompt = (
            "You are an expert in steel Mill Test Certificates (MTC) per EN 10204. "
            "Extract the following fields from the MTC text and return a JSON object. "
            "For each field include its value and a confidence score (0.0–1.0). "
            "Use null for missing fields. Do not include any text outside the JSON object.\n\n"
            "Required JSON structure:\n"
            "{\n"
            '  "certificate_number": {"value": ..., "confidence": ...},\n'
            '  "heat_number": {"value": ..., "confidence": ...},\n'
            '  "steel_grade": {"value": ..., "confidence": ...},\n'
            '  "standard": {"value": ..., "confidence": ...},\n'
            '  "production_route": {"value": "BF-BOF"|"EAF"|"DRI-EAF"|null, "confidence": ...},\n'
            '  "melt_country_iso": {"value": "GB"|"DE"|...|null, "confidence": ...},\n'
            '  "pour_country_iso": {"value": "GB"|"DE"|...|null, "confidence": ...},\n'
            '  "melt_location": {"value": ..., "confidence": ...},\n'
            '  "pour_location": {"value": ..., "confidence": ...},\n'
            '  "issue_date": {"value": "YYYY-MM-DD"|null, "confidence": ...},\n'
            '  "net_weight_tonnes": {"value": ..., "confidence": ...},\n'
            '  "chemical_composition": {\n'
            '    "C": {"value": ..., "confidence": ...},\n'
            '    "Si": {"value": ..., "confidence": ...},\n'
            '    "Mn": {"value": ..., "confidence": ...},\n'
            '    "P": {"value": ..., "confidence": ...},\n'
            '    "S": {"value": ..., "confidence": ...},\n'
            '    "Cr": {"value": ..., "confidence": ...},\n'
            '    "Mo": {"value": ..., "confidence": ...},\n'
            '    "Ni": {"value": ..., "confidence": ...},\n'
            '    "V": {"value": ..., "confidence": ...}\n'
            "  },\n"
            '  "mechanical_properties": {\n'
            '    "tensile_strength_mpa": {"value": ..., "confidence": ...},\n'
            '    "yield_strength_mpa": {"value": ..., "confidence": ...},\n'
            '    "elongation_pct": {"value": ..., "confidence": ...}\n'
            "  },\n"
            '  "cbam_see_tco2_per_t": {"value": ..., "confidence": ...},\n'
            '  "warnings": []\n'
            "}"
        )

        user_prompt = (
            f"Mill Test Certificate text from '{filename}':\n\n"
            f"{raw_text[:6000]}"
        )

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
            max_tokens=1500,
        )

        raw_json = response.choices[0].message.content or "{}"
        # Strip markdown code fences if present
        raw_json = raw_json.strip()
        if raw_json.startswith("```"):
            raw_json = raw_json.split("```")[1]
            if raw_json.startswith("json"):
                raw_json = raw_json[4:]
        extracted = json.loads(raw_json)

    except json.JSONDecodeError as exc:
        logger.error("MTC extraction JSON parse error: %s", exc)
        extracted = {}
    except Exception as exc:
        logger.error("MTC extraction OpenAI error: %s", exc)
        from app.engines.base import EngineError
        raise EngineError("AI_ERROR", f"OpenAI MTC extraction failed: {exc}")

    # ── Post-process: add status flags ────────────────────────────────────
    warnings: list[str] = list(extracted.get("warnings", []))

    if not raw_text.strip():
        warnings.append(
            "No text could be extracted from the PDF. "
            "This may be a scanned image — results may be inaccurate."
        )

    # Sanctions check on melt/pour country
    melt = extracted.get("melt_country_iso", {})
    pour = extracted.get("pour_country_iso", {})
    melt_val = (melt.get("value") or "").upper() if isinstance(melt, dict) else ""
    pour_val = (pour.get("value") or "").upper() if isinstance(pour, dict) else ""

    hard_block = False
    if melt_val in ("RU", "BY"):
        warnings.append(
            f"HARD BLOCK: Melt country '{melt_val}' detected. "
            "Russian/Belarusian melt origin is prohibited under UK/EU sanctions. "
            "This shipment cannot proceed."
        )
        hard_block = True
    if pour_val in ("RU", "BY"):
        warnings.append(
            f"HARD BLOCK: Pour country '{pour_val}' detected. "
            "Russian/Belarusian pour origin is prohibited under UK/EU sanctions. "
            "This shipment cannot proceed."
        )
        hard_block = True

    extracted["warnings"] = warnings
    extracted["hard_block"] = hard_block
    extracted["filename"] = filename
    extracted["raw_text_length"] = len(raw_text)
    extracted["source"] = "OpenAI gpt-4o (MTC extraction)"

    return extracted
