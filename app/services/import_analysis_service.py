"""
Import Analysis Service — top-level orchestrator.

Sequence:
  1. Normalize request fields.
  2. Classify product via hs_classifier_service (OpenAI Responses API).
  3. Fetch tariff data (duty rate + trade measures) via tariff_service.
  4. Fetch VAT rate via vat_service.
  5. Evaluate preferential origin eligibility via origin_rules_service.
  6. Calculate CIF value and landed cost via money utils.
  7. Assemble and return ImportAnalysisResponse.

The AI is only used in step 2.  All financial figures come exclusively from
the data adapters (steps 3 and 4).
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

from app.schemas.import_analysis import (
    CalculationResult,
    ImportAnalysisRequest,
    ImportAnalysisResponse,
    SourceRecord,
)
from app.services import (
    hs_classifier_service,
    origin_rules_service,
    tariff_service,
    vat_service,
)
from app.utils import money as money_util

logger = logging.getLogger(__name__)


async def analyze(request: ImportAnalysisRequest) -> ImportAnalysisResponse:
    """
    Run the full import analysis pipeline and return a structured response.

    Steps 3, 4, and 5 are executed concurrently via asyncio.gather() after
    the HS classification (step 2) completes, since they are independent.
    """
    logger.info(
        "import_analysis_service: start origin=%s dest=%s desc='%s...'",
        request.origin_country,
        request.destination_country,
        request.product_description[:60],
    )

    # ── Step 2: HS Classification ─────────────────────────────────────────
    classification = await hs_classifier_service.classify(
        product_description=request.product_description,
        origin_country=request.origin_country,
        destination_country=request.destination_country,
        extended_description=request.goods_description_extended,
        quantity_unit=request.quantity_unit,
        manufacturer_name=request.manufacturer_name,
    )

    hs_code = classification.primary_hs_code

    # ── Steps 3, 4, 5: concurrent data fetches ───────────────────────────
    tariff_data, vat_data, origin_rules = await asyncio.gather(
        tariff_service.fetch(
            hs_code=hs_code,
            origin=request.origin_country,
            destination=request.destination_country,
        ),
        vat_service.fetch(
            destination=request.destination_country,
            hs_code=hs_code,
        ),
        origin_rules_service.evaluate(
            origin=request.origin_country,
            destination=request.destination_country,
            hs_code=hs_code,
            duty_rate=tariff_data.duty_rate if hasattr(tariff_data, "duty_rate") else None,
        ),
    )

    # ── Step 6: Calculate landed cost ────────────────────────────────────
    calculation = _build_calculation(
        request=request,
        duty_rate=tariff_data.duty_rate,
        vat_rate=vat_data.vat_rate,
        preferential_rate=origin_rules.preferential_duty_rate if origin_rules.preferential_eligible else None,
    )

    # ── Step 7: Assemble response ─────────────────────────────────────────
    from app.config import settings

    rates_result = _build_rates(
        duty_rate=tariff_data.duty_rate,
        vat_rate=vat_data.vat_rate,
        origin_rules=origin_rules,
    )

    measures_result = tariff_service.to_measures(tariff_data)
    compliance_result = tariff_service.to_compliance(tariff_data)

    # Merge origin-rules notes into compliance
    if origin_rules.notes:
        compliance_result.notes.extend(origin_rules.notes)
    if origin_rules.proof_of_origin_required:
        compliance_result.documents_required.append(
            f"Proof of origin: {origin_rules.proof_of_origin_required}"
        )
    if vat_data.vat_notes:
        compliance_result.notes.extend(vat_data.vat_notes)

    sources = [
        SourceRecord(
            type="ai_classification",
            provider="OpenAI",
            model=settings.openai_classification_model,
        ),
        SourceRecord(type="tariff_data", provider="tariff_adapter"),
        SourceRecord(type="vat_data", provider="vat_adapter"),
    ]

    logger.info(
        "import_analysis_service: done hs=%s confidence=%.2f duty=%.1f%% vat=%.1f%%",
        hs_code,
        classification.confidence,
        tariff_data.duty_rate or 0.0,
        vat_data.vat_rate or 0.0,
    )

    return ImportAnalysisResponse(
        success=True,
        input=request,
        classification=classification,
        rates=rates_result,
        measures=measures_result,
        compliance=compliance_result,
        calculation=calculation,
        sources=sources,
    )


def _build_rates(
    *,
    duty_rate: Optional[float],
    vat_rate: Optional[float],
    origin_rules,
) -> "RatesResult":
    from app.schemas.import_analysis import RatesResult
    return RatesResult(
        duty_rate=duty_rate,
        vat_rate=vat_rate,
        preferential_duty_rate=origin_rules.preferential_duty_rate,
        preferential_eligible=origin_rules.preferential_eligible,
        preferential_agreement=origin_rules.agreement_name,
    )


def _build_calculation(
    *,
    request: ImportAnalysisRequest,
    duty_rate: Optional[float],
    vat_rate: Optional[float],
    preferential_rate: Optional[float],
) -> CalculationResult:
    """Build the CalculationResult, running the math if enough data is available."""

    if request.customs_value is None:
        # No value provided — return structure only, no amounts
        return CalculationResult(
            cif_value=None,
            duty_amount=None,
            vat_amount=None,
            total_landed_cost=None,
            currency=request.currency,
            duty_basis="customs_value (not provided — supply customs_value for calculation)",
            vat_basis="CIF value + import duty (standard EU basis)",
        )

    # Use preferential rate if eligible and it's actually lower than MFN
    effective_duty_rate = duty_rate or 0.0
    if preferential_rate is not None and preferential_rate < effective_duty_rate:
        effective_duty_rate = preferential_rate

    effective_vat_rate = vat_rate or 0.0

    breakdown = money_util.calculate_landed_cost(
        customs_value=request.customs_value,
        freight=request.freight,
        insurance=request.insurance,
        incoterms=request.incoterms,
        duty_rate_pct=effective_duty_rate,
        vat_rate_pct=effective_vat_rate,
        currency=request.currency,
    )

    return CalculationResult(
        cif_value=breakdown.cif_value,
        duty_amount=breakdown.duty_amount,
        vat_amount=breakdown.vat_amount,
        total_landed_cost=breakdown.total_landed_cost,
        currency=request.currency,
        duty_basis=breakdown.duty_basis_note,
        vat_basis=breakdown.vat_basis_note,
    )
