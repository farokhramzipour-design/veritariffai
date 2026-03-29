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
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.deps import CurrentUser, get_current_user
from app.core.responses import ok
from app.domain.plan import PlanTier
from app.infrastructure.database.models import CalculationProfile, FREE_TIER_PROFILE_LIMIT
from app.infrastructure.database.session import get_session
from app.schemas.import_analysis import ImportAnalysisRequest, ImportAnalysisResponse
from app.services import import_analysis_service

logger = logging.getLogger(__name__)

router = APIRouter()

FREE_LIMIT = FREE_TIER_PROFILE_LIMIT  # 5


async def _count_profiles(db: AsyncSession, user_uuid: UUID) -> int:
    result = await db.execute(
        select(func.count(CalculationProfile.id)).where(
            CalculationProfile.user_id == user_uuid
        )
    )
    return result.scalar_one()


@router.post(
    "",
    response_model=ImportAnalysisResponse,
    summary="Analyse import duties, origin, and compliance for a product",
    response_description=(
        "Full import analysis including HS classification, duty rates, VAT, "
        "preferential eligibility, trade measures, and compliance requirements."
    ),
)
async def import_analysis(
    request: ImportAnalysisRequest,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> ImportAnalysisResponse:
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
    uid = UUID(user.id)

    # Enforce free-tier profile limit before doing any expensive work
    if user.plan == PlanTier.FREE:
        count = await _count_profiles(db, uid)
        if count >= FREE_LIMIT:
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "FREE_TIER_LIMIT",
                    "message": (
                        f"Free users can save up to {FREE_LIMIT} analysis profiles. "
                        "Upgrade to PRO for unlimited profiles."
                    ),
                    "limit": FREE_LIMIT,
                    "current_count": count,
                },
            )

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

    # Persist the analysis as a calculation profile
    profile = CalculationProfile(
        id=uuid4(),
        user_id=uid,
        name=request.profile_name,
        description=request.profile_description,
        shipment_data={
            "origin": request.origin_country,
            "destination": request.destination_country,
            "currency": request.currency,
            "incoterms": request.incoterms,
        },
        lines_data=[{
            "product_description": request.product_description,
            "customs_value": request.customs_value,
            "freight": request.freight,
            "insurance": request.insurance,
            "quantity": request.quantity,
            "quantity_unit": request.quantity_unit,
            "manufacturer_name": request.manufacturer_name,
            "goods_description_extended": request.goods_description_extended,
        }],
        last_result=result.model_dump(mode="json"),
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)

    result.profile_id = str(profile.id)
    return result
