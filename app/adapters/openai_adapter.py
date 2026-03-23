"""
OpenAI adapter — HS classification via the OpenAI Responses API.

Design constraints enforced at the prompt level:
  - The model ONLY produces HS classification output.
  - It MUST NOT invent duty rates, VAT rates, or any financial figures.
  - Confidence must be honest: uncertainty is expressed through a lower score
    and by populating missing_attributes.

SDK requirement: openai >= 1.66.0 (Responses API support).
"""
from __future__ import annotations

import json
import logging
from typing import Any

from openai import AsyncOpenAI, APIError

from app.config import settings
from app.schemas.import_analysis import HSClassificationRaw

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Strict JSON schema for structured output
# This schema is sent verbatim to the OpenAI Responses API.
# The model's output will be validated against it before returning.
# ---------------------------------------------------------------------------

_HS_CLASSIFICATION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "primary_hs_code": {
            "type": "string",
            "description": (
                "The most likely HS code at 6-digit precision (or more if the product "
                "detail justifies it). Digits only — no dots or spaces."
            ),
        },
        "confidence": {
            "type": "number",
            "description": (
                "Confidence in the primary_hs_code. 0.0 = completely uncertain, "
                "1.0 = fully certain. Must not exceed 0.95 for 6-digit codes when "
                "product description is ambiguous."
            ),
        },
        "alternative_hs_codes": {
            "type": "array",
            "items": {"type": "string"},
            "description": "1–3 other plausible HS codes in descending likelihood. Empty list if none.",
        },
        "reasoning_summary": {
            "type": "string",
            "description": (
                "Plain-language explanation of why this HS code was chosen, referencing "
                "the GRI rule applied. Max 300 characters."
            ),
        },
        "missing_attributes": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                "Attributes that, if provided, would increase classification confidence. "
                "For example: 'fiber composition', 'intended end-use', 'gender'. "
                "Empty list if confidence >= 0.90."
            ),
        },
    },
    "required": [
        "primary_hs_code",
        "confidence",
        "alternative_hs_codes",
        "reasoning_summary",
        "missing_attributes",
    ],
    "additionalProperties": False,
}

# ---------------------------------------------------------------------------
# System prompt — deterministic, domain-constrained
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are a certified customs classification expert with deep knowledge of the \
Harmonized System (HS/CN/TARIC) nomenclature.

YOUR TASK
Classify the product described by the user into the correct HS code.

ABSOLUTE RULES — NEVER VIOLATE THESE
1. ONLY produce the JSON schema output — no duty rates, VAT rates, taxes, or \
financial figures of any kind.
2. Base your classification SOLELY on the product description and attributes provided.
3. NEVER invent, guess, or assume legal rates, tariff schedules, or official duty percentages.
4. If you are uncertain about the classification, lower the confidence score and \
populate missing_attributes with what additional information would help.

CONFIDENCE CALIBRATION
0.90–1.00 : highly certain of the 6-digit or more specific code
0.75–0.89 : confident in the chapter/heading, uncertain about the exact subheading
0.50–0.74 : significant product attributes are missing — classify at heading level only
0.00–0.49 : only chapter-level classification is defensible

HS PRECISION RULE
Default to 6-digit (international subheading) precision.
Use 8- or 10-digit precision ONLY when the product description explicitly supplies \
the distinguishing attribute (e.g. gender, fibre %, intended use, power rating).

CLASSIFICATION METHOD — follow GRI in order
GRI 1: Classify by the terms of the heading and section/chapter notes.
GRI 2: Incomplete/unfinished goods; mixtures.
GRI 3: Most specific description takes precedence; essential character.
GRI 4: Most akin goods.
GRI 5: Packing materials.
GRI 6: Subheading level classification.

OUTPUT FORMAT
Return the JSON object matching exactly the schema provided. No other text.\
"""


def _build_user_message(
    product_description: str,
    origin_country: str,
    destination_country: str,
    extended_description: str | None,
    quantity_unit: str | None,
    manufacturer_name: str | None,
) -> str:
    """Construct the user message sent to the model."""
    parts = [f"Product description: {product_description}"]

    if extended_description:
        parts.append(f"Extended technical detail: {extended_description}")
    if origin_country:
        parts.append(f"Country of origin: {origin_country}")
    if destination_country:
        parts.append(f"Importing country: {destination_country}")
    if quantity_unit:
        parts.append(f"Unit of measure: {quantity_unit}")
    if manufacturer_name:
        parts.append(f"Manufacturer: {manufacturer_name}")

    parts.append("\nClassify this product.")
    return "\n".join(parts)


async def classify_hs_code(
    *,
    product_description: str,
    origin_country: str,
    destination_country: str,
    extended_description: str | None = None,
    quantity_unit: str | None = None,
    manufacturer_name: str | None = None,
) -> HSClassificationRaw:
    """
    Call the OpenAI Responses API to classify a product into an HS code.

    Uses structured output (json_schema format) so the model's response
    always conforms to HSClassificationRaw regardless of phrasing.

    Raises:
        RuntimeError: If the OpenAI API key is not configured.
        APIError:     On OpenAI transport/API failures.
        ValueError:   If the model output cannot be parsed into HSClassificationRaw.
    """
    if not settings.openai_api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not configured. Set it in the environment or .env file."
        )

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    model = settings.openai_classification_model

    user_message = _build_user_message(
        product_description=product_description,
        origin_country=origin_country,
        destination_country=destination_country,
        extended_description=extended_description,
        quantity_unit=quantity_unit,
        manufacturer_name=manufacturer_name,
    )

    logger.info(
        "openai_adapter: classify_hs_code model=%s origin=%s dest=%s desc_len=%d",
        model,
        origin_country,
        destination_country,
        len(product_description),
    )

    try:
        response = await client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            text={
                "format": {
                    "type": "json_schema",
                    # SDK v2.x: schema fields are nested under "json_schema", not flat
                    "json_schema": {
                        "name": "hs_classification_result",
                        "strict": True,
                        "schema": _HS_CLASSIFICATION_SCHEMA,
                    },
                }
            },
        )

        raw_text: str = response.output_text
        logger.debug("openai_adapter: raw output: %s", raw_text[:500])

    except APIError as exc:
        logger.error("openai_adapter: OpenAI API error: %s", exc)
        raise

    # Parse and validate the structured output
    try:
        data: dict[str, Any] = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        logger.error("openai_adapter: JSON parse failure: %s | raw=%s", exc, raw_text[:300])
        raise ValueError(f"OpenAI returned invalid JSON: {exc}") from exc

    try:
        result = HSClassificationRaw.model_validate(data)
    except Exception as exc:
        logger.error("openai_adapter: schema validation failure: %s | data=%s", exc, data)
        raise ValueError(f"OpenAI output did not match HSClassificationRaw schema: {exc}") from exc

    logger.info(
        "openai_adapter: classified → hs=%s confidence=%.2f review=%s",
        result.primary_hs_code,
        result.confidence,
        result.confidence < settings.import_analysis_confidence_threshold,
    )
    return result
