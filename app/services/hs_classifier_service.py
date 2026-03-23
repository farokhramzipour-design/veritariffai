"""
HS Classifier Service.

Thin orchestration layer between the API router and the OpenAI adapter.
Adds the business rule: confidence < threshold → review_required = True.
"""
from __future__ import annotations

import logging

from app.adapters.openai_adapter import classify_hs_code
from app.config import settings
from app.schemas.import_analysis import HSClassificationRaw, HSClassificationResult

logger = logging.getLogger(__name__)


async def classify(
    *,
    product_description: str,
    origin_country: str,
    destination_country: str,
    extended_description: str | None = None,
    quantity_unit: str | None = None,
    manufacturer_name: str | None = None,
) -> HSClassificationResult:
    """
    Classify a product into an HS code and apply the review_required business rule.

    Delegates to the OpenAI adapter for AI classification, then enriches the
    result with the review_required flag based on the configured confidence threshold.
    """
    raw: HSClassificationRaw = await classify_hs_code(
        product_description=product_description,
        origin_country=origin_country,
        destination_country=destination_country,
        extended_description=extended_description,
        quantity_unit=quantity_unit,
        manufacturer_name=manufacturer_name,
    )

    threshold = settings.import_analysis_confidence_threshold
    review_required = raw.confidence < threshold

    if review_required:
        logger.info(
            "hs_classifier_service: review required — confidence=%.2f < threshold=%.2f hs=%s",
            raw.confidence,
            threshold,
            raw.primary_hs_code,
        )

    return HSClassificationResult(
        primary_hs_code=raw.primary_hs_code,
        confidence=raw.confidence,
        alternative_hs_codes=raw.alternative_hs_codes,
        reasoning_summary=raw.reasoning_summary,
        missing_attributes=raw.missing_attributes,
        review_required=review_required,
    )
