from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.calculations.schemas import (
    CalculationRequest,
    ProfileCreate,
    ProfileUpdate,
)
from app.application.calculations.orchestrator import calculate_sync
from app.core.deps import CurrentUser, get_current_user, require_plan
from app.core.responses import ok
from app.domain.plan import PlanTier
from app.infrastructure.database.models import CalculationProfile, FREE_TIER_PROFILE_LIMIT
from app.infrastructure.database.session import get_session

router = APIRouter()

FREE_LIMIT = FREE_TIER_PROFILE_LIMIT  # 5


# ── Helper ────────────────────────────────────────────────────────────────────

def _profile_to_dict(p: CalculationProfile) -> dict:
    return {
        "id": str(p.id),
        "user_id": str(p.user_id),
        "name": p.name,
        "description": p.description,
        "shipment_data": p.shipment_data,
        "lines_data": p.lines_data,
        "last_result": p.last_result,
        "created_at": p.created_at.isoformat(),
        "updated_at": p.updated_at.isoformat(),
    }


# ── Calculation profiles (registered before /{param} routes) ─────────────────

@router.post(
    "/profiles",
    summary="Save a new calculation profile",
    status_code=201,
    tags=["calculation-profiles"],
)
async def create_profile(
    payload: ProfileCreate,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """
    Create a named, saved calculation profile.

    **Free tier:** maximum **5** profiles. Returns HTTP 403 when the limit is reached.
    PRO users have no limit.
    """
    if user.plan == PlanTier.FREE:
        count_result = await db.execute(
            select(func.count()).where(CalculationProfile.user_id == user.id)
        )
        count = count_result.scalar_one()
        if count >= FREE_LIMIT:
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "FREE_TIER_LIMIT",
                    "message": (
                        f"Free users can save up to {FREE_LIMIT} calculation profiles. "
                        "Upgrade to PRO for unlimited profiles."
                    ),
                    "limit": FREE_LIMIT,
                    "current_count": count,
                },
            )

    profile = CalculationProfile(
        id=str(uuid4()),
        user_id=user.id,
        name=payload.name,
        description=payload.description,
        shipment_data=payload.shipment_data,
        lines_data=payload.lines_data,
        last_result=None,
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return ok(_profile_to_dict(profile))


@router.get(
    "/profiles",
    summary="List the current user's calculation profiles",
    tags=["calculation-profiles"],
)
async def list_profiles(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    total_result = await db.execute(
        select(func.count()).where(CalculationProfile.user_id == user.id)
    )
    total = total_result.scalar_one()

    rows_result = await db.execute(
        select(CalculationProfile)
        .where(CalculationProfile.user_id == user.id)
        .order_by(CalculationProfile.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )
    profiles = rows_result.scalars().all()

    is_free = user.plan == PlanTier.FREE
    return ok({
        "results": [_profile_to_dict(p) for p in profiles],
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": (offset + limit) < total,
        "free_tier_limit": FREE_LIMIT if is_free else None,
        "remaining_slots": max(0, FREE_LIMIT - total) if is_free else None,
    })


@router.get(
    "/profiles/{profile_id}",
    summary="Get a single calculation profile",
    tags=["calculation-profiles"],
)
async def get_profile(
    profile_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    result = await db.execute(
        select(CalculationProfile).where(
            CalculationProfile.id == profile_id,
            CalculationProfile.user_id == user.id,
        )
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found.")
    return ok(_profile_to_dict(profile))


@router.patch(
    "/profiles/{profile_id}",
    summary="Edit a calculation profile",
    tags=["calculation-profiles"],
)
async def update_profile(
    profile_id: str,
    payload: ProfileUpdate,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """
    Partially update a profile. Only fields present in the request body are changed.
    """
    result = await db.execute(
        select(CalculationProfile).where(
            CalculationProfile.id == profile_id,
            CalculationProfile.user_id == user.id,
        )
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found.")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)

    await db.commit()
    await db.refresh(profile)
    return ok(_profile_to_dict(profile))


@router.delete(
    "/profiles/{profile_id}",
    summary="Delete a calculation profile",
    tags=["calculation-profiles"],
)
async def delete_profile(
    profile_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    result = await db.execute(
        select(CalculationProfile).where(
            CalculationProfile.id == profile_id,
            CalculationProfile.user_id == user.id,
        )
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found.")
    await db.delete(profile)
    await db.commit()
    return ok({"deleted": True, "id": profile_id})


# ── Existing calculation run endpoints ────────────────────────────────────────

@router.post("/sync")
async def calculate_sync_endpoint(
    payload: CalculationRequest,
    user: CurrentUser = Depends(get_current_user),
):
    result = calculate_sync(payload)
    data = {
        "request_id": str(uuid4()),
        "status": "complete",
        "confidence_score": result.confidence / 100,
        "totals": {
            "customs_value": {"amount": str(result.breakdown.total), "currency": "GBP"},
            "total_duty": {"amount": "0.00", "currency": "GBP"},
            "total_vat": {"amount": "0.00", "currency": "GBP"},
            "total_excise": {"amount": "0.00", "currency": "GBP"},
            "total_clearance": {"amount": "0.00", "currency": "GBP"},
            "total_landed_cost": {"amount": str(result.breakdown.total), "currency": "GBP"},
        },
        "line_results": [],
        "warnings": [],
        "audit_trail_available": True,
        "engines_used": ["classification", "tariff_measure", "vat", "fx"],
    }
    return ok(data)


@router.post("/async")
async def calculate_async_endpoint(
    payload: CalculationRequest,
    user: CurrentUser = Depends(require_plan(PlanTier.PRO)),
):
    task_id = str(uuid4())
    return ok({"task_id": task_id, "status": "pending", "poll_url": f"/api/v1/calculations/{task_id}/status"})


@router.get("/{task_id}/status")
async def calc_status(task_id: str):
    return ok({"task_id": task_id, "status": "processing", "progress": {"lines_processed": 0, "lines_total": 0}})


@router.get("/{request_id}/result")
async def calc_result(request_id: str):
    return ok({"request_id": request_id, "status": "complete"})


@router.get("/{request_id}/audit")
async def calc_audit(request_id: str, user: CurrentUser = Depends(require_plan(PlanTier.PRO))):
    return ok({"steps": [{"sequence": 1, "engine": "customs_valuation", "step_name": "incoterm_gap_adjustment", "formula_description": "FOB origin", "input_snapshot": {}, "output_snapshot": {"customs_value": "9250.00"}}]})


@router.get("")
async def calc_list(
    limit: int = Query(20),
    offset: int = Query(0),
    status_q: str | None = Query(None),
    from_date: str | None = Query(None),
    to_date: str | None = Query(None),
    user: CurrentUser = Depends(get_current_user),
):
    return ok({"results": [], "total": 0, "limit": limit, "offset": offset, "has_more": False})


@router.delete("/{request_id}")
async def calc_delete(request_id: str, user: CurrentUser = Depends(get_current_user)):
    return ok({"deleted": True})
