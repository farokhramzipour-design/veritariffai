"""
Rules of Origin (ROO) API – Steps 2.1-2.4 of the Veritariff Happy Path.

Implements the UK-EU Trade and Cooperation Agreement (TCA) preferential
origin gateway.

Endpoints
---------
POST /origin/roo
    Run the ROO check:
      – Validate TCA threshold (sufficient processing / wholly obtained)
      – Determine applicable preferential rate
      – Return COO/ROO statement-on-origin recommendation
      – Flag whether an origin declaration is required

POST /origin/declaration
    Record / validate a signed origin declaration for a shipment.

References
----------
UK Trade Tariff API  : api.trade-tariff.service.gov.uk
EU TARIC ROO         : ec.europa.eu/taxation_customs/dds2/taric
UK-EU TCA Origin     : GOV.UK SR 2020/1432, Annex ORIG
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.responses import ok

router = APIRouter()

# ---------------------------------------------------------------------------
# UK-EU TCA: agreements where UK origin goods may claim preferential rates
# ---------------------------------------------------------------------------
_UK_EU_TCA_AGREEMENTS = {"UK-EU-TCA", "TCA", "UKGTS"}
_EU_COUNTRIES = {
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR",
    "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL",
    "PL", "PT", "RO", "SK", "SI", "ES", "SE",
}
_UK_COUNTRIES = {"GB", "UK"}


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class ROOCheckRequest(BaseModel):
    """
    Input for the Rules of Origin check (Happy Path Step 2.1 – 2.4).
    """

    hs_code: str = Field(..., description="10-digit commodity code (or 6-digit heading)")
    origin_country: str = Field(..., description="ISO-2 country of manufacture / processing")
    destination_country: str = Field(..., description="ISO-2 import destination country")

    # Production / processing evidence
    wholly_obtained: bool = Field(
        False,
        description="True if the goods are wholly obtained in the origin country",
    )
    last_substantial_transformation_country: Optional[str] = Field(
        None,
        description="ISO-2 country where last substantial transformation occurred",
    )
    regional_value_content_pct: Optional[float] = Field(
        None,
        ge=0,
        le=100,
        description="Regional Value Content percentage (RVC) if applicable",
    )

    # TCA-specific
    tca_preference_claimed: bool = Field(
        False, description="Whether the exporter intends to claim TCA preferential rate"
    )
    exporter_ref: Optional[str] = Field(None, description="Exporter reference / EORI")
    shipment_value_gbp: Optional[float] = Field(
        None, ge=0, description="Total shipment value in GBP (used for de minimis check)"
    )


class ROOAuditStep(BaseModel):
    step: str
    result: str
    detail: str


class ROOCheckResponse(BaseModel):
    origin_country: str
    destination_country: str
    hs_code: str
    tca_eligible: bool
    preferential_rate_available: bool
    agreement: Optional[str] = None
    origin_status: str = Field(
        ...,
        description="WHOLLY_OBTAINED | SUFFICIENT_PROCESSING | INSUFFICIENT_PROCESSING | UNKNOWN",
    )
    rvc_threshold_met: Optional[bool] = None
    origin_declaration_required: bool
    origin_declaration_type: Optional[str] = Field(
        None,
        description="STATEMENT_ON_ORIGIN | REX_DECLARATION | EUR1 | ATR | NONE",
    )
    coo_statement_text: Optional[str] = Field(
        None, description="Recommended statement-on-origin text"
    )
    audit_trail: List[ROOAuditStep] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class OriginDeclarationRequest(BaseModel):
    """Record/validate a signed Statement on Origin."""

    shipment_ref: str = Field(..., description="Shipment or calculation request reference")
    hs_code: str
    origin_country: str
    destination_country: str
    exporter_ref: str = Field(..., description="Exporter EORI or reference number")
    declaration_text: str = Field(..., description="Full statement-on-origin text as signed")
    signed: bool = Field(..., description="Confirms the declaration has been physically signed")


class OriginDeclarationResponse(BaseModel):
    shipment_ref: str
    status: str  # ACCEPTED | REJECTED
    reason: Optional[str] = None
    declaration_id: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# ROO engine logic
# ---------------------------------------------------------------------------

_TCA_RVC_THRESHOLD = 50.0  # % – default sufficient-processing threshold under TCA
_DE_MINIMIS_GBP = 135.0    # Low-value consignment threshold


def _run_roo_check(req: ROOCheckRequest) -> ROOCheckResponse:
    """
    Lightweight Rules-of-Origin engine implementing the UK-EU TCA gateway
    from the Veritariff Happy Path (Steps 2.1 – 2.4).
    """
    audit: list[ROOAuditStep] = []
    warnings: list[str] = []

    origin = req.origin_country.upper()
    dest = req.destination_country.upper()
    hs = "".join(ch for ch in req.hs_code if ch.isdigit())
    chapter = hs[:2] if len(hs) >= 2 else "??"

    # ------------------------------------------------------------------
    # Step 2.1 – Is TCA applicable?
    # ------------------------------------------------------------------
    uk_to_eu = origin in _UK_COUNTRIES and dest in _EU_COUNTRIES
    eu_to_uk = origin in _EU_COUNTRIES and dest in _UK_COUNTRIES
    tca_eligible = uk_to_eu or eu_to_uk

    audit.append(ROOAuditStep(
        step="2.1_tca_gateway",
        result="ELIGIBLE" if tca_eligible else "NOT_ELIGIBLE",
        detail=(
            f"UK→EU: {uk_to_eu}, EU→UK: {eu_to_uk}. "
            "TCA applies between GB and EU member states."
        ),
    ))

    if not tca_eligible:
        warnings.append(
            f"Trade route {origin}→{dest} is not covered by the UK-EU TCA. "
            "Preferential rates under TCA are not available."
        )

    # ------------------------------------------------------------------
    # Step 2.2 – Origin status determination
    # ------------------------------------------------------------------
    origin_status = "UNKNOWN"
    rvc_threshold_met: Optional[bool] = None

    if req.wholly_obtained:
        origin_status = "WHOLLY_OBTAINED"
        audit.append(ROOAuditStep(
            step="2.2_origin_status",
            result="WHOLLY_OBTAINED",
            detail="Goods declared as wholly obtained in the origin country.",
        ))
    elif req.regional_value_content_pct is not None:
        rvc = req.regional_value_content_pct
        rvc_threshold_met = rvc >= _TCA_RVC_THRESHOLD
        if rvc_threshold_met:
            origin_status = "SUFFICIENT_PROCESSING"
            audit.append(ROOAuditStep(
                step="2.2_rvc_check",
                result="PASS",
                detail=f"RVC {rvc}% ≥ threshold {_TCA_RVC_THRESHOLD}% → sufficient processing.",
            ))
        else:
            origin_status = "INSUFFICIENT_PROCESSING"
            audit.append(ROOAuditStep(
                step="2.2_rvc_check",
                result="FAIL",
                detail=f"RVC {rvc}% < threshold {_TCA_RVC_THRESHOLD}% → insufficient processing.",
            ))
            warnings.append(
                f"RVC {rvc}% is below the TCA threshold of {_TCA_RVC_THRESHOLD}%. "
                "Preferential treatment may be denied."
            )
    elif req.last_substantial_transformation_country:
        lst_country = req.last_substantial_transformation_country.upper()
        if lst_country == origin:
            origin_status = "SUFFICIENT_PROCESSING"
            audit.append(ROOAuditStep(
                step="2.2_last_substantial_transformation",
                result="PASS",
                detail=f"Last substantial transformation occurred in {origin} (origin country).",
            ))
        else:
            origin_status = "INSUFFICIENT_PROCESSING"
            audit.append(ROOAuditStep(
                step="2.2_last_substantial_transformation",
                result="FAIL",
                detail=(
                    f"Last substantial transformation in {lst_country}, "
                    f"but declared origin is {origin}."
                ),
            ))
            warnings.append(
                "Last substantial transformation country differs from declared origin. "
                "Origin claim may not be valid."
            )
    else:
        warnings.append(
            "Neither wholly_obtained, regional_value_content_pct, nor "
            "last_substantial_transformation_country provided. "
            "Origin status cannot be conclusively determined; manual verification required."
        )

    # ------------------------------------------------------------------
    # Step 2.3 – Chapter 72 steel-specific RoO note
    # ------------------------------------------------------------------
    if chapter == "72":
        audit.append(ROOAuditStep(
            step="2.3_chapter_72_roo_note",
            result="INFO",
            detail=(
                "Chapter 72 (iron and steel): TCA typically requires manufacture from "
                "materials of any heading (CTH rule) or a specific chemical/processing "
                "threshold. Verify the applicable PSR (Product-Specific Rule) in "
                "Annex ORIG-2 of the TCA."
            ),
        ))
        warnings.append(
            "Chapter 72 goods: verify the Product-Specific Rule (PSR) in TCA Annex ORIG-2 "
            "before claiming preferential origin."
        )

    # ------------------------------------------------------------------
    # Step 2.4 – Origin declaration type
    # ------------------------------------------------------------------
    preferential_rate_available = tca_eligible and origin_status in (
        "WHOLLY_OBTAINED", "SUFFICIENT_PROCESSING"
    )

    origin_declaration_required = preferential_rate_available and req.tca_preference_claimed
    declaration_type: Optional[str] = None
    coo_text: Optional[str] = None
    agreement: Optional[str] = None

    if preferential_rate_available:
        agreement = "UK-EU TCA (SR 2020/1432)"
        if req.tca_preference_claimed:
            # Shipments ≤ GBP 6,000 may use a simple statement; above requires REX or approved-exporter
            shipment_val = req.shipment_value_gbp or 0.0
            if shipment_val <= 6000 or shipment_val == 0:
                declaration_type = "STATEMENT_ON_ORIGIN"
                coo_text = (
                    "The exporter of the products covered by this document "
                    f"(Exporter Reference: {req.exporter_ref or 'UNKNOWN'}) declares that, "
                    "except where otherwise clearly indicated, these products are of "
                    f"{origin} preferential origin."
                )
            else:
                declaration_type = "REX_DECLARATION"
                coo_text = (
                    "For shipments exceeding EUR/GBP 6,000 a Registered Exporter (REX) "
                    "statement on origin is required. The exporter must be registered in "
                    "the REX system."
                )
                warnings.append(
                    "Shipment value exceeds GBP 6,000. A REX statement on origin is required; "
                    "ensure the exporter is registered in the REX system."
                )
        else:
            declaration_type = "NONE"
            warnings.append(
                "TCA preference not claimed by exporter; MFN duty rates will apply."
            )

    if origin_declaration_required:
        audit.append(ROOAuditStep(
            step="2.4_origin_declaration",
            result=declaration_type or "NONE",
            detail=f"Origin declaration type: {declaration_type}. Agreement: {agreement}.",
        ))

    return ROOCheckResponse(
        origin_country=origin,
        destination_country=dest,
        hs_code=req.hs_code,
        tca_eligible=tca_eligible,
        preferential_rate_available=preferential_rate_available,
        agreement=agreement,
        origin_status=origin_status,
        rvc_threshold_met=rvc_threshold_met,
        origin_declaration_required=origin_declaration_required,
        origin_declaration_type=declaration_type,
        coo_statement_text=coo_text,
        audit_trail=audit,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/roo", response_model=dict, summary="Rules of Origin check (UK-EU TCA gateway)")
async def roo_check(body: ROOCheckRequest):
    """
    Run the UK-EU TCA Rules of Origin gateway (Happy Path Steps 2.1 – 2.4).

    Checks whether the goods qualify for preferential tariff treatment under
    the UK-EU Trade and Cooperation Agreement, determines the origin status
    (wholly obtained / sufficient processing / insufficient), and returns the
    recommended origin declaration type plus COO statement text.
    """
    result = _run_roo_check(body)
    return ok(result.model_dump())


@router.post(
    "/declaration",
    response_model=dict,
    summary="Record and validate a signed origin declaration",
)
async def origin_declaration(body: OriginDeclarationRequest):
    """
    Record and validate a Statement on Origin or REX declaration.

    The clearance gate (Step 4) will block release until
    `origin_declaration.status == 'SIGNED'` when a TCA preference has been
    claimed.  Calling this endpoint with `signed=True` marks the declaration
    as accepted and stores the reference.
    """
    import hashlib
    import uuid

    warnings: list[str] = []

    if not body.signed:
        return ok(
            OriginDeclarationResponse(
                shipment_ref=body.shipment_ref,
                status="REJECTED",
                reason="Declaration has not been signed. Set signed=true to record acceptance.",
                warnings=warnings,
            ).model_dump()
        )

    if not body.declaration_text.strip():
        return ok(
            OriginDeclarationResponse(
                shipment_ref=body.shipment_ref,
                status="REJECTED",
                reason="declaration_text must not be empty.",
                warnings=warnings,
            ).model_dump()
        )

    # Generate a deterministic declaration ID from shipment_ref + exporter + text
    raw = f"{body.shipment_ref}:{body.exporter_ref}:{body.declaration_text}"
    declaration_id = str(uuid.UUID(hashlib.md5(raw.encode()).hexdigest()))

    # Chapter 72 advisory note
    hs_chapter = "".join(ch for ch in body.hs_code if ch.isdigit())[:2]
    if hs_chapter == "72":
        warnings.append(
            "Chapter 72 goods: ensure PSR compliance has been verified against "
            "TCA Annex ORIG-2 before filing the origin declaration."
        )

    return ok(
        OriginDeclarationResponse(
            shipment_ref=body.shipment_ref,
            status="ACCEPTED",
            declaration_id=declaration_id,
            warnings=warnings,
        ).model_dump()
    )
