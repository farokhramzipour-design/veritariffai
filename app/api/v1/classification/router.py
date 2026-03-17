"""
Classification API – Step 1 of the Veritariff Happy Path.

Endpoints
---------
POST /classification/steel
    Run the Chapter-72 steel decision tree.
    Returns the 4-digit HS heading, steel class, audit trail, and warnings.

POST /classification/pre-check
    Before triggering the full classification engine, verify whether the
    commodity code was already determined in the calculation flow (mirrors
    the "already classified?" gate in the Happy Path flowchart).
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.responses import ok
from app.engines.base import EngineError
from app.engines.steel_classification import (
    MaterialType,
    MetalForm,
    SteelClassificationInput,
    classify_steel,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class SteelClassifyRequest(BaseModel):
    """
    Inputs for the Chapter-72 steel classification engine.

    material_type is always required.
    For STEEL, also supply the chemical composition percentages and the
    physical form.  For non-steel materials (waste, pig iron, ferro-alloy,
    etc.) only material_type (and optionally carbon_pct / manganese_pct for
    pig iron sub-classification) is needed.
    """

    material_type: MaterialType = Field(
        ...,
        description=(
            "Primary material category: waste_or_scrap | granules_or_powders | "
            "direct_reduction_sponge_iron | pig_iron | ferro_alloy | steel"
        ),
    )
    carbon_pct: Optional[float] = Field(None, ge=0, le=100, description="Carbon content (%)")
    chromium_pct: Optional[float] = Field(None, ge=0, le=100, description="Chromium content (%)")
    manganese_pct: Optional[float] = Field(None, ge=0, le=100, description="Manganese content (%)")
    aluminium_pct: Optional[float] = Field(None, ge=0, le=100, description="Aluminium content (%)")
    silicon_pct: Optional[float] = Field(None, ge=0, le=100, description="Silicon content (%)")
    nickel_pct: Optional[float] = Field(None, ge=0, le=100, description="Nickel content (%)")
    molybdenum_pct: Optional[float] = Field(None, ge=0, le=100, description="Molybdenum content (%)")
    form: Optional[MetalForm] = Field(
        None,
        description=(
            "Physical form: ingots | primary_forms | semi_finished | flat_rolled | "
            "bars_rods_hot_rolled_irregular_coils | bars_rods_other | angles | "
            "shapes | sections | hollow_drill_bars | wire | angles_shapes"
        ),
    )
    width_mm: Optional[float] = Field(
        None, ge=0, description="Width in mm (required for flat_rolled products)"
    )


class AuditStepOut(BaseModel):
    step_name: str
    formula_description: str
    input_snapshot: dict
    output_snapshot: dict


class SteelClassifyResponse(BaseModel):
    heading: str = Field(..., description="4-digit HS heading (e.g. '7219')")
    chapter: str = Field("72", description="HS chapter")
    steel_class: Optional[str] = Field(None, description="STAINLESS_STEEL | OTHER_ALLOY_STEEL | NON_ALLOY_IRON_STEEL")
    reasoning: str = Field(..., description="Human-readable explanation of the classification path")
    audit_trail: List[AuditStepOut] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Pre-check request / response
# ---------------------------------------------------------------------------


class PreClassificationCheckRequest(BaseModel):
    """
    Check whether a commodity code has already been resolved in the
    calculator flow before triggering the full classification engine.
    """

    hs_code: Optional[str] = Field(
        None, description="The HS/commodity code already present in the flow (if any)"
    )
    description: Optional[str] = Field(None, description="Product description for context")


class PreClassificationCheckResponse(BaseModel):
    already_classified: bool
    hs_code: Optional[str] = None
    proceed_to_engine: bool
    message: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/steel", response_model=dict, summary="Chapter-72 Steel Classification Engine")
async def classify_steel_endpoint(body: SteelClassifyRequest):
    """
    Run the Veritariff Chapter-72 steel decision tree (Happy Path Steps 1.1–1.2C).

    Returns the 4-digit HS heading, the steel alloy class (where applicable),
    a human-readable reasoning string, an audit trail, and any warnings.
    The caller should append the appropriate 6-digit subheading using the
    UK Trade Tariff / TARIC lookup to obtain the full 10-digit commodity code.
    """
    inp = SteelClassificationInput(
        material_type=body.material_type,
        carbon_pct=body.carbon_pct,
        chromium_pct=body.chromium_pct,
        manganese_pct=body.manganese_pct,
        aluminium_pct=body.aluminium_pct,
        silicon_pct=body.silicon_pct,
        nickel_pct=body.nickel_pct,
        molybdenum_pct=body.molybdenum_pct,
        form=body.form,
        width_mm=body.width_mm,
    )
    try:
        result = classify_steel(inp)
    except EngineError as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail={"code": exc.code, "message": exc.message})

    response = SteelClassifyResponse(
        heading=result.heading,
        chapter=result.chapter,
        steel_class=result.steel_class.value if result.steel_class else None,
        reasoning=result.reasoning,
        audit_trail=[
            AuditStepOut(
                step_name=s.step_name,
                formula_description=s.formula_description,
                input_snapshot=s.input_snapshot,
                output_snapshot=s.output_snapshot,
            )
            for s in result.audit_steps
        ],
        warnings=result.warnings,
    )
    return ok(response.model_dump())


@router.post(
    "/pre-check",
    response_model=dict,
    summary="Pre-classification check – was the code already determined?",
)
async def pre_classification_check(body: PreClassificationCheckRequest):
    """
    Mirrors the 'Already classified?' gate in the Happy Path flowchart.

    If an HS code has already been determined earlier in the calculator flow,
    display the 'Classified tick' and skip the full classification engine.
    Otherwise, instruct the caller to proceed to Step 1.
    """
    hs = (body.hs_code or "").strip()
    # A valid declarable commodity code must be 8-10 digits
    digits = "".join(ch for ch in hs if ch.isdigit())
    already_classified = len(digits) >= 6

    if already_classified:
        payload = PreClassificationCheckResponse(
            already_classified=True,
            hs_code=hs,
            proceed_to_engine=False,
            message=(
                f"Code {hs} was already determined in the calculator flow. "
                "Displaying classified tick in the workflow timeline. "
                "Full classification engine will not be re-triggered."
            ),
        )
    else:
        payload = PreClassificationCheckResponse(
            already_classified=False,
            hs_code=None,
            proceed_to_engine=True,
            message="No valid commodity code found. Proceed to the full classification engine (Step 1.1).",
        )

    return ok(payload.model_dump())
