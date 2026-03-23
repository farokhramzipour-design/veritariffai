"""
Shipment management API.

Provides CRUD for the core Shipment object that accumulates data across all
7 workflow steps.  Each user owns their own shipments; free users are limited
to 5 active shipments (same quota as calculation profiles).

All routes are protected (JWT required via the parent router dependency).
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, get_current_user
from app.core.responses import ok
from app.infrastructure.database.session import get_session
from app.infrastructure.database.models import CalculationProfile

router = APIRouter()

_FREE_TIER_LIMIT = 5

# ---------------------------------------------------------------------------
# In-memory shipment store
# (replace with DB table in production — structure mirrors CalculationProfile)
# ---------------------------------------------------------------------------

_shipments: Dict[str, Dict[str, Any]] = {}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _gen_ref() -> str:
    """Generate a human-readable shipment reference VT-YYYY-NNNN."""
    year = datetime.now(timezone.utc).year
    short = str(uuid.uuid4().int)[:4]
    return f"VT-{year}-{short.zfill(4)}"


def _user_shipments(user_id: str) -> List[Dict[str, Any]]:
    return [s for s in _shipments.values() if s["user_id"] == user_id]


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class ShipmentCreateRequest(BaseModel):
    hs_code: str = Field(..., description="HS commodity code (6–10 digits)")
    corridor: str = Field(..., description="Trade corridor, e.g. 'UK-DE'")
    goods_description: Optional[str] = None
    origin_country: str = Field(..., description="ISO-2 country of origin")
    destination_country: str = Field(..., description="ISO-2 destination country")
    weight_tonnes: Optional[float] = Field(None, description="Net shipment weight (tonnes)")
    customs_value_gbp: Optional[float] = Field(None, description="CIF customs value in GBP")
    supplementary_units: Optional[str] = Field(None, description="e.g. '500 t'")
    notes: Optional[str] = None


class ShipmentPatchRequest(BaseModel):
    hs_code: Optional[str] = None
    corridor: Optional[str] = None
    goods_description: Optional[str] = None
    origin_country: Optional[str] = None
    destination_country: Optional[str] = None
    weight_tonnes: Optional[float] = None
    customs_value_gbp: Optional[float] = None
    supplementary_units: Optional[str] = None
    notes: Optional[str] = None
    # Step results
    origin_status: Optional[str] = None          # PREFERENTIAL | NON_PREFERENTIAL | PENDING
    duty_rate_applied: Optional[float] = None
    regulatory_flags: Optional[List[str]] = None  # ['CBAM', 'TRQ_CAT26', 'MELT_POUR']
    cbam_applicable: Optional[bool] = None
    cbam_see_actual: Optional[float] = None
    cbam_see_default: Optional[float] = None
    cbam_saving: Optional[float] = None
    sanctions_cleared: Optional[bool] = None
    melt_country_iso: Optional[str] = None
    pour_country_iso: Optional[str] = None
    heat_number: Optional[str] = None
    statement_of_origin: Optional[Dict[str, Any]] = None
    mtc_hash: Optional[str] = None
    cds_mrn: Optional[str] = None
    step_status: Optional[Dict[str, str]] = None  # {1: 'complete', 2: 'active', ...}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("", response_model=dict, status_code=201, summary="Create a new shipment")
async def create_shipment(
    body: ShipmentCreateRequest,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """
    Create a new shipment and return the shipment object.

    Free users are limited to 5 shipments.  Each shipment starts at Step 1
    (classification) with all subsequent steps in PENDING status.
    """
    # Quota check (reuse CalculationProfile count as proxy for free plan)
    from uuid import UUID as _UUID
    user_uuid = _UUID(user.id)

    existing = _user_shipments(user.id)
    if user.plan.upper() == "FREE" and len(existing) >= _FREE_TIER_LIMIT:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "QUOTA_EXCEEDED",
                "message": (
                    f"Free plan allows up to {_FREE_TIER_LIMIT} shipments. "
                    "Upgrade to Pro for unlimited shipments."
                ),
                "limit": _FREE_TIER_LIMIT,
                "used": len(existing),
            },
        )

    hs = "".join(ch for ch in body.hs_code if ch.isdigit())
    shipment_id = str(uuid.uuid4())
    ref = _gen_ref()
    now = _now()

    shipment: Dict[str, Any] = {
        "id": shipment_id,
        "ref": ref,
        "user_id": user.id,
        "corridor": body.corridor.upper(),
        "hs_code": hs,
        "goods_description": body.goods_description,
        "origin_country": body.origin_country.upper(),
        "destination_country": body.destination_country.upper(),
        "weight_tonnes": body.weight_tonnes,
        "customs_value_gbp": body.customs_value_gbp,
        "supplementary_units": body.supplementary_units,
        "notes": body.notes,
        # Step results (populated as user progresses)
        "origin_status": "PENDING",
        "duty_rate_applied": None,
        "regulatory_flags": [],
        "cbam_applicable": None,
        "cbam_see_actual": None,
        "cbam_see_default": None,
        "cbam_saving": None,
        "sanctions_cleared": None,
        "melt_country_iso": None,
        "pour_country_iso": None,
        "heat_number": None,
        "statement_of_origin": None,
        "mtc_hash": None,
        "cds_mrn": None,
        "documents": [],
        "workspace_participants": [],
        "step_status": {
            "1": "pending",
            "2": "pending",
            "3": "pending",
            "4": "pending",
            "5": "pending",
            "6": "pending",
            "7": "pending",
        },
        "created_at": now,
        "updated_at": now,
    }

    _shipments[shipment_id] = shipment
    return ok(shipment)


@router.get("", response_model=dict, summary="List all shipments for the current user")
async def list_shipments(
    user: CurrentUser = Depends(get_current_user),
):
    """Return all shipments owned by the authenticated user, newest first."""
    items = sorted(
        _user_shipments(user.id),
        key=lambda s: s["created_at"],
        reverse=True,
    )
    return ok({"shipments": items, "total": len(items)})


@router.get("/{shipment_id}", response_model=dict, summary="Get a shipment by ID")
async def get_shipment(
    shipment_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Return a single shipment object.  Returns 404 if not found or not owned by user."""
    shipment = _shipments.get(shipment_id)
    if not shipment or shipment["user_id"] != user.id:
        raise HTTPException(status_code=404, detail=f"Shipment '{shipment_id}' not found.")
    return ok(shipment)


@router.patch("/{shipment_id}", response_model=dict, summary="Update shipment fields")
async def patch_shipment(
    shipment_id: str,
    body: ShipmentPatchRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """
    Partially update a shipment.

    Clients send only the fields they want to change.  All provided non-None
    values overwrite the stored values; omitted fields (None) are left unchanged.
    This is how each step pushes its results into the shared shipment object.
    """
    shipment = _shipments.get(shipment_id)
    if not shipment or shipment["user_id"] != user.id:
        raise HTTPException(status_code=404, detail=f"Shipment '{shipment_id}' not found.")

    patch = body.model_dump(exclude_none=True)
    if "hs_code" in patch:
        patch["hs_code"] = "".join(ch for ch in patch["hs_code"] if ch.isdigit())
    if "origin_country" in patch:
        patch["origin_country"] = patch["origin_country"].upper()
    if "destination_country" in patch:
        patch["destination_country"] = patch["destination_country"].upper()

    # Merge step_status dict rather than replace
    if "step_status" in patch and isinstance(shipment.get("step_status"), dict):
        shipment["step_status"].update(patch.pop("step_status"))

    shipment.update(patch)
    shipment["updated_at"] = _now()
    return ok(shipment)


@router.delete("/{shipment_id}", response_model=dict, summary="Delete a shipment")
async def delete_shipment(
    shipment_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Permanently delete a shipment and all associated data."""
    shipment = _shipments.get(shipment_id)
    if not shipment or shipment["user_id"] != user.id:
        raise HTTPException(status_code=404, detail=f"Shipment '{shipment_id}' not found.")
    del _shipments[shipment_id]
    return ok({"deleted": True, "shipment_id": shipment_id})
