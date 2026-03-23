"""
Import Analysis API router.

POST /api/v1/import-analysis

Accepts product details and trade lane information, returns:
  - AI-generated HS classification (via OpenAI Responses API)
  - Official duty rate (from tariff adapter)
  - VAT/import tax rate (from VAT adapter)
  - Preferential duty eligibility (from origin rules engine)
  - Anti-dumping / countervailing measures
  - Required documents and compliance notes
  - Landed cost calculation
"""
from __future__ import annotations

import logging
import sys
import traceback

from fastapi import APIRouter, HTTPException

from app.config import settings
from app.core.responses import ok
from app.schemas.import_analysis import ImportAnalysisRequest, ImportAnalysisResponse
from app.services import import_analysis_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "",
    response_model=ImportAnalysisResponse,
    summary="Analyse import duties, origin, and compliance for a product",
    response_description=(
        "Full import analysis including HS classification, duty rates, VAT, "
        "preferential eligibility, trade measures, and compliance requirements."
    ),
)
async def import_analysis(request: ImportAnalysisRequest) -> ImportAnalysisResponse:
    """
    ## Import Analysis

    Performs end-to-end import analysis for a product shipment:

    1. **AI Classification** — Uses the OpenAI Responses API to classify the product
       into the most likely HS code. Confidence ≥ 0.75 is recommended before relying
       on the result for declarations. If confidence is below the threshold,
       `review_required` will be `true` and `missing_attributes` will guide what
       additional product information would help.

    2. **Duty Rate** — Retrieved from the official tariff data adapter (EU CCT/TARIC
       for EU destinations, UK Global Tariff for GB). The AI never produces rates.

    3. **VAT / Import Tax** — Retrieved from the VAT adapter. The AI never produces
       VAT figures.

    4. **Preferential Eligibility** — Evaluated by the origin rules engine against
       the applicable trade agreement (TCA, GSP, EPA, etc.).

    5. **Trade Measures** — Anti-dumping, countervailing, and excise duties from
       the tariff adapter.

    6. **Landed Cost** — Calculated if `customs_value` is provided (CIF basis).

    > **Note:** Duty and VAT amounts are estimates for planning purposes.
    > Official rates must be verified at the applicable customs authority before
    > lodging a declaration.
    """
    logger.info(
        "import_analysis: received origin=%s dest=%s desc='%s...'",
        request.origin_country,
        request.destination_country,
        request.product_description[:50],
    )

    try:
        result = await import_analysis_service.analyze(request)
    except RuntimeError as exc:
        # Configuration errors (e.g. missing API key)
        tb = traceback.format_exc()
        print(f"[import_analysis 503] {type(exc).__name__}: {exc}\n{tb}", file=sys.stderr, flush=True)
        logger.error("import_analysis: config error: %s", exc, exc_info=True)
        raise HTTPException(status_code=503, detail=str(exc))
    except ValueError as exc:
        # Malformed AI output or validation errors
        tb = traceback.format_exc()
        print(f"[import_analysis 422] {type(exc).__name__}: {exc}\n{tb}", file=sys.stderr, flush=True)
        logger.error("import_analysis: validation error: %s", exc, exc_info=True)
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        tb = traceback.format_exc()
        print(f"[import_analysis 500] {type(exc).__name__}: {exc}\n{tb}", file=sys.stderr, flush=True)
        logger.error(
            "import_analysis: unhandled %s: %s\n%s",
            type(exc).__name__, exc, tb,
        )
        detail: str | dict
        if settings.debug or settings.environment != "production":
            detail = {
                "error": type(exc).__name__,
                "message": str(exc),
                "traceback": tb.splitlines()[-5:],   # last 5 lines
            }
        else:
            detail = "Import analysis failed. See server logs."
        raise HTTPException(status_code=500, detail=detail)

    return result
