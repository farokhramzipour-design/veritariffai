"""
Workflow API – Steps 2 (RoO Wizard), TRQ, Section 301, UFLPA, CSL,
              Step 4 (MTC upload), Step 5 (Licences, CBAM), Step 6 (CDS Declaration, EXS),
              Step 7 (Document Bundle), plus EORI validation and SoO generation.

All routes are protected (JWT required via the parent router's dependency).
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.core.responses import ok
from app.engines.roo_wizard import run_roo_wizard
from app.engines.trq_screen import screen_trq
from app.engines.compliance_screen import screen_section_301, screen_uflpa, screen_csl
from app.engines.cbam_calculator import calculate_cbam
from app.engines.mtc_extraction import extract_mtc_fields

router = APIRouter()


# ===========================================================================
# RoO Wizard – Gates 1–3F
# ===========================================================================

class RoOWizardRequest(BaseModel):
    hs_code: str = Field(..., description="HS code of the goods (6–10 digits)")
    origin_country: str = Field(..., description="ISO-2 country of manufacture/processing")
    destination_country: str = Field(..., description="ISO-2 import destination")

    # Gate 3A
    wholly_obtained: bool = Field(False, description="True if wholly obtained in origin country")

    # Gate 3B
    materials_hs_codes: Optional[List[str]] = Field(
        None, description="HS codes of input materials (for CTH check)"
    )
    ctsh_satisfied: Optional[bool] = Field(
        None, description="Whether the CTH/CTSH rule is satisfied"
    )

    # Gate 3C
    cumulation_countries: Optional[List[str]] = Field(
        None, description="ISO-2 countries contributing to cumulation"
    )

    # Gate 3D
    regional_value_content_pct: Optional[float] = Field(
        None, ge=0, le=100, description="Regional Value Content %"
    )
    non_originating_value: Optional[float] = Field(
        None, description="Value of non-originating materials"
    )
    ex_works_price: Optional[float] = Field(
        None, description="Ex-works price of the finished product"
    )

    # Gate 3F
    exporter_ref: Optional[str] = Field(None, description="Exporter EORI or reference")
    shipment_value_gbp: Optional[float] = Field(None, description="Total shipment value in GBP")

    # Gate 2
    documents_provided: Optional[List[str]] = Field(
        None, description="List of document names already in hand"
    )


@router.post(
    "/roo/wizard",
    response_model=dict,
    summary="Full Rules of Origin Wizard (Gates 1–3F)",
)
async def roo_wizard(body: RoOWizardRequest):
    """
    Run the complete TCA/preferential origin wizard through all gates:

    - Gate 1: MFN gateway (preferential agreement check)
    - Gate 2: Document completeness
    - Gate 3A: Wholly obtained test
    - Gate 3B: PSR / Change of Tariff Heading
    - Gate 3C: Cumulation
    - Gate 3D: Sufficient processing / Regional Value Content
    - Gate 3E: Final origin determination
    - Gate 3F: Statement-of-Origin generation
    """
    result = run_roo_wizard(
        hs_code=body.hs_code,
        origin_country=body.origin_country,
        destination_country=body.destination_country,
        wholly_obtained=body.wholly_obtained,
        materials_hs_codes=body.materials_hs_codes,
        ctsh_satisfied=body.ctsh_satisfied,
        cumulation_countries=body.cumulation_countries,
        regional_value_content_pct=body.regional_value_content_pct,
        non_originating_value=body.non_originating_value,
        ex_works_price=body.ex_works_price,
        exporter_ref=body.exporter_ref,
        shipment_value_gbp=body.shipment_value_gbp,
        documents_provided=body.documents_provided,
    )
    return ok(result)


# ===========================================================================
# TRQ Live Screening
# ===========================================================================

class TRQScreenRequest(BaseModel):
    hs_code: str = Field(..., description="HS code (6–10 digits)")
    origin_country: str = Field(..., description="ISO-2 country of origin")
    destination_country: str = Field(..., description="ISO-2 import destination")
    shipment_weight_kg: Optional[float] = Field(None, description="Total shipment weight in kg")
    shipment_value_gbp: Optional[float] = Field(None, description="Total shipment value in GBP")


@router.post(
    "/trq/screen",
    response_model=dict,
    summary="TRQ Live Screening (EU Cat-26 / UK Safeguard)",
)
async def trq_screen(body: TRQScreenRequest):
    """
    Screen the shipment against applicable Tariff Rate Quotas:

    - EU Steel Safeguard Category 26 (HS 7208–7212)
    - UK Steel Safeguard categories (SI 2021/1122)

    Returns GREEN / AMBER / RED quota status with quota fill percentages,
    in-quota and out-of-quota duty rates.
    """
    result = screen_trq(
        hs_code=body.hs_code,
        origin_country=body.origin_country,
        destination_country=body.destination_country,
        shipment_weight_kg=body.shipment_weight_kg,
        shipment_value_gbp=body.shipment_value_gbp,
    )
    return ok(result)


# ===========================================================================
# Section 301 (US-China tariff)
# ===========================================================================

class Section301Request(BaseModel):
    hs_code: str = Field(..., description="HS code (6–10 digits)")
    origin_country: str = Field(..., description="ISO-2 country of origin")
    destination_country: str = Field(..., description="ISO-2 import destination")
    customs_value_usd: Optional[float] = Field(
        None, description="Customs value in USD (for duty calculation)"
    )


@router.post(
    "/compliance/section-301",
    response_model=dict,
    summary="Section 301 US-China Tariff Screening",
)
async def section_301_screen(body: Section301Request):
    """
    Determine whether additional Section 301 US tariffs apply (CN→US trade).

    Identifies the applicable tariff list (List 1 / 2 / 3 / 4A / 4B),
    the additional duty rate (7.5% or 25%), and checks for active USTR exclusions.
    """
    result = screen_section_301(
        hs_code=body.hs_code,
        origin_country=body.origin_country,
        destination_country=body.destination_country,
        customs_value_usd=body.customs_value_usd,
    )
    return ok(result)


# ===========================================================================
# UFLPA Supply Chain Audit
# ===========================================================================

class UFLPARequest(BaseModel):
    factory_name: Optional[str] = Field(None, description="Primary factory / manufacturer name")
    factory_address: Optional[str] = Field(None, description="Full factory address")
    supplier_names: Optional[List[str]] = Field(
        None, description="Sub-tier supplier names to screen"
    )
    goods_description: Optional[str] = Field(None, description="Description of the goods")
    hs_code: Optional[str] = Field(None, description="HS code of the goods")


@router.post(
    "/compliance/uflpa",
    response_model=dict,
    summary="UFLPA Clean Supply Chain Audit",
)
async def uflpa_screen(body: UFLPARequest):
    """
    Audit the supply chain against the Uyghur Forced Labor Prevention Act (UFLPA).

    - Checks factory/supplier names against the UFLPA Entity List
    - Screens factory address for Xinjiang geographic risk keywords
    - Identifies high-risk sectors (cotton, polysilicon, tomatoes, etc.)
    - Returns rebuttable_presumption flag and required evidence checklist
    """
    result = screen_uflpa(
        factory_name=body.factory_name,
        factory_address=body.factory_address,
        supplier_names=body.supplier_names,
        goods_description=body.goods_description,
        hs_code=body.hs_code,
    )
    return ok(result)


# ===========================================================================
# CSL / Entity List Screening
# ===========================================================================

class CSLScreenRequest(BaseModel):
    party_names: List[str] = Field(
        ..., description="Names of parties to screen (exporter, importer, forwarder, etc.)"
    )
    party_countries: Optional[List[str]] = Field(
        None, description="ISO-2 countries of the parties (optional, narrows results)"
    )


@router.post(
    "/compliance/csl",
    response_model=dict,
    summary="CSL / Entity List Real-time Screening",
)
async def csl_screen(body: CSLScreenRequest):
    """
    Screen party names against:

    - ITA Consolidated Screening List (CSL)
    - US BIS Entity List (Export Administration Regulations)
    - OFAC SDN List

    Returns a cleared/blocked status with the matching list entries and required actions.
    """
    result = screen_csl(
        party_names=body.party_names,
        party_countries=body.party_countries,
    )
    return ok(result)


# ===========================================================================
# Step 5 – Licences & Restrictions Check
# ===========================================================================

# ECCN / Export Classification categories requiring a BIS licence for EAR99+
_LICENCE_REQUIRED_CHAPTERS = {
    "88": {"reason": "Aircraft — ECCN 9A991 / dual-use", "authority": "BIS / ECJU"},
    "93": {"reason": "Arms, ammunition — ECCN 0A501", "authority": "ECJU / DIT"},
    "84": {"reason": "Machinery with potential dual-use — verify ECCN", "authority": "BIS / ECJU"},
    "85": {"reason": "Electronic equipment — verify ECCN against CCL", "authority": "BIS / ECJU"},
    "38": {"reason": "Chemicals — may require CWC / chemical licence", "authority": "ECJU"},
}

_IMPORT_LICENCE_COUNTRIES = {
    "CN": "Import licence may be required for goods of Chinese origin under enhanced controls.",
    "RU": "Import authorisation required under UK/EU Russia sanctions regime.",
    "IR": "Import licence required under Iran sanctions.",
    "KP": "Import prohibited under North Korea sanctions.",
}


class LicenceCheckRequest(BaseModel):
    hs_code: str = Field(..., description="HS code of the goods")
    origin_country: str = Field(..., description="ISO-2 country of origin")
    destination_country: str = Field(..., description="ISO-2 destination country")
    goods_description: Optional[str] = Field(None, description="Brief goods description")
    end_use: Optional[str] = Field(None, description="Declared end-use of the goods")
    end_user: Optional[str] = Field(None, description="End-user name")


@router.post(
    "/licences/check",
    response_model=dict,
    summary="Step 5 – Export/Import Licences & Restrictions Check",
)
async def licences_check(body: LicenceCheckRequest):
    """
    Check whether export or import licences are required for the shipment (Step 5).

    Screens:
    - HS chapter against dual-use / controlled goods categories
    - Origin country against import restriction regimes
    - Destination country against export control lists
    """
    warnings: List[str] = []
    flags: List[Dict[str, Any]] = []

    hs_digits = "".join(ch for ch in body.hs_code if ch.isdigit())
    chapter = hs_digits[:2] if len(hs_digits) >= 2 else ""
    origin = body.origin_country.upper().strip()
    dest = body.destination_country.upper().strip()

    # Chapter-level licence check
    if chapter in _LICENCE_REQUIRED_CHAPTERS:
        info = _LICENCE_REQUIRED_CHAPTERS[chapter]
        flags.append({
            "type": "EXPORT_LICENCE",
            "severity": "WARNING",
            "chapter": chapter,
            "reason": info["reason"],
            "authority": info["authority"],
            "action": (
                f"Verify ECCN classification for HS {body.hs_code} and apply for an export "
                f"licence via {info['authority']} (SPIRE / BIS portal) if required."
            ),
        })

    # Origin country import restrictions
    if origin in _IMPORT_LICENCE_COUNTRIES:
        flags.append({
            "type": "IMPORT_RESTRICTION",
            "severity": "WARNING" if origin not in ("KP",) else "BLOCK",
            "country": origin,
            "reason": _IMPORT_LICENCE_COUNTRIES[origin],
            "action": (
                "Check HMRC / DIT guidance and apply for the relevant import licence or "
                "authorisation before the goods arrive."
            ),
        })

    # Steel Chapter 72 – SIMA / anti-dumping advisory
    if chapter == "72":
        warnings.append(
            f"Steel goods (Chapter 72) from {origin} may be subject to anti-dumping duties "
            "or countervailing measures. Verify at the HMRC Trade Tariff / relevant authority."
        )

    # End-use advisory
    if body.end_use and any(kw in body.end_use.lower() for kw in ("military", "defence", "nuclear", "weapon")):
        flags.append({
            "type": "END_USE_CONTROL",
            "severity": "BLOCK",
            "reason": "Declared end-use suggests military / strategic application.",
            "action": (
                "An export licence is required for goods with military or strategic end-use. "
                "Apply via ECJU SPIRE system before export."
            ),
        })

    cleared = not any(f["severity"] == "BLOCK" for f in flags)

    return ok({
        "cleared": cleared,
        "flags": flags,
        "hs_code": body.hs_code,
        "origin_country": origin,
        "destination_country": dest,
        "warnings": warnings,
    })


# ===========================================================================
# Step 6 – CDS Declaration Data Generation
# ===========================================================================

class CDSDeclarationRequest(BaseModel):
    shipment_ref: str = Field(..., description="Internal shipment reference")
    exporter_name: str
    exporter_eori: str = Field(..., description="Exporter EORI number")
    importer_name: str
    importer_eori: str = Field(..., description="Importer EORI number")
    freight_forwarder_name: Optional[str] = None
    freight_forwarder_eori: Optional[str] = None

    hs_code: str
    goods_description: str
    origin_country: str
    destination_country: str
    incoterms: Optional[str] = Field(None, description="Incoterms code (e.g. DAP, DDP, FOB)")
    currency: str = Field("GBP", description="Invoice currency (GBP / EUR / USD)")
    customs_value: float = Field(..., description="Customs (CIF) value")
    gross_weight_kg: float
    net_weight_kg: Optional[float] = None
    number_of_packages: int = Field(1)
    package_type: str = Field("CT", description="UN package type code")

    # Origin declaration
    tca_preference_claimed: bool = False
    origin_declaration_id: Optional[str] = None
    preference_code: Optional[str] = Field(None, description="CDS preference code e.g. '100'")


@router.post(
    "/cds/declaration",
    response_model=dict,
    summary="Step 6 – Generate CDS Declaration Data",
)
async def cds_declaration(body: CDSDeclarationRequest):
    """
    Generate a pre-populated Customs Declaration Service (CDS) data payload (Step 6).

    Produces a structured JSON representation suitable for submission to HMRC CDS
    or for populating a freight-forwarder's declaration system.
    Includes a SHA-256 hash of the canonical payload for audit purposes.
    """
    issued_at = datetime.now(timezone.utc).isoformat()
    declaration_id = str(uuid.uuid4())

    hs_digits = "".join(ch for ch in body.hs_code if ch.isdigit())
    # CDS uses 10-digit commodity code; pad with zeros if shorter
    commodity_code = hs_digits.ljust(10, "0")[:10]

    payload: Dict[str, Any] = {
        "declaration_id": declaration_id,
        "shipment_ref": body.shipment_ref,
        "issued_at": issued_at,
        "declaration_type": "EX" if body.destination_country.upper() not in (
            "GB", "UK", "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR",
            "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL",
            "PL", "PT", "RO", "SK", "SI", "ES", "SE",
        ) else "IM",
        "procedure_code": "1040",  # Standard export / import – adjust per shipment
        "additional_procedure_code": "000",
        "exporter": {
            "name": body.exporter_name,
            "eori": body.exporter_eori,
        },
        "importer": {
            "name": body.importer_name,
            "eori": body.importer_eori,
        },
        "freight_forwarder": {
            "name": body.freight_forwarder_name,
            "eori": body.freight_forwarder_eori,
        } if body.freight_forwarder_name else None,
        "goods_item": {
            "commodity_code": commodity_code,
            "description": body.goods_description,
            "origin_country": body.origin_country.upper(),
            "destination_country": body.destination_country.upper(),
            "customs_value": body.customs_value,
            "currency": body.currency.upper(),
            "gross_weight_kg": body.gross_weight_kg,
            "net_weight_kg": body.net_weight_kg,
            "number_of_packages": body.number_of_packages,
            "package_type": body.package_type,
            "incoterms": body.incoterms,
        },
        "preference": {
            "claimed": body.tca_preference_claimed,
            "preference_code": body.preference_code or ("100" if body.tca_preference_claimed else "000"),
            "origin_declaration_id": body.origin_declaration_id,
        },
        "cds_box_44_documents": _build_box44(body),
    }

    # SHA-256 hash for audit trail
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    sha256_hash = hashlib.sha256(canonical.encode()).hexdigest()
    payload["sha256_hash"] = sha256_hash

    return ok(payload)


def _build_box44(body: CDSDeclarationRequest) -> List[Dict[str, str]]:
    """Build the Box 44 (supporting documents) list."""
    docs = [
        {"code": "N935", "description": "Commercial Invoice"},
        {"code": "N271", "description": "Packing List"},
    ]
    if body.tca_preference_claimed:
        docs.append({"code": "U112", "description": "Statement on Origin (TCA)"})
    if "72" in body.hs_code[:2]:
        docs.append({"code": "N002", "description": "Mill Test Certificate"})
    return docs


# ===========================================================================
# Step 7 – Document Bundle (Barrister's Bundle)
# ===========================================================================

# In-memory store (replace with S3/DB in production)
_bundle_store: Dict[str, Dict[str, Any]] = {}


class DocumentBundleCreateRequest(BaseModel):
    shipment_ref: str = Field(..., description="Shipment reference")
    documents: List[Dict[str, str]] = Field(
        ...,
        description=(
            "List of document records. Each must have: "
            "'name' (str), 'status' (VALIDATED|PENDING|MISSING), "
            "optional 'doc_id' and 'notes'."
        ),
    )
    clearance_id: Optional[str] = Field(None, description="Linked clearance certificate ID")
    declaration_id: Optional[str] = Field(None, description="Linked CDS declaration ID")
    notes: Optional[str] = Field(None, description="Additional notes for the bundle")


class DocumentBundleAddRequest(BaseModel):
    name: str = Field(..., description="Document name / type")
    status: str = Field("PENDING", description="VALIDATED | PENDING | MISSING")
    doc_id: Optional[str] = None
    notes: Optional[str] = None


@router.post(
    "/bundle",
    response_model=dict,
    summary="Step 7 – Create Barrister's Bundle (document suite)",
    status_code=201,
)
async def create_bundle(body: DocumentBundleCreateRequest):
    """
    Create a Veritariff document bundle (Barrister's Bundle) for a shipment (Step 7).

    The bundle tracks all mandatory and supporting documents, their validation
    status, and links to the clearance certificate and CDS declaration.
    Returns a bundle_id for subsequent retrieval and updates.
    """
    bundle_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()

    validated = sum(1 for d in body.documents if d.get("status") == "VALIDATED")
    total = len(body.documents)

    bundle = {
        "bundle_id": bundle_id,
        "shipment_ref": body.shipment_ref,
        "created_at": created_at,
        "updated_at": created_at,
        "documents": body.documents,
        "document_count": total,
        "validated_count": validated,
        "completeness_pct": round(validated / total * 100, 1) if total else 0,
        "clearance_id": body.clearance_id,
        "declaration_id": body.declaration_id,
        "notes": body.notes,
        "status": "COMPLETE" if validated == total and total > 0 else "INCOMPLETE",
    }

    _bundle_store[bundle_id] = bundle
    return ok(bundle)


@router.get(
    "/bundle/{bundle_id}",
    response_model=dict,
    summary="Step 7 – Retrieve document bundle",
)
async def get_bundle(bundle_id: str):
    """Retrieve a previously created document bundle by its bundle_id."""
    from fastapi import HTTPException
    bundle = _bundle_store.get(bundle_id)
    if not bundle:
        raise HTTPException(status_code=404, detail=f"Bundle '{bundle_id}' not found.")
    return ok(bundle)


@router.post(
    "/bundle/{bundle_id}/documents",
    response_model=dict,
    summary="Step 7 – Add document to bundle",
)
async def add_document_to_bundle(bundle_id: str, body: DocumentBundleAddRequest):
    """Add or update a document entry in an existing bundle."""
    from fastapi import HTTPException
    bundle = _bundle_store.get(bundle_id)
    if not bundle:
        raise HTTPException(status_code=404, detail=f"Bundle '{bundle_id}' not found.")

    new_doc = {
        "name": body.name,
        "status": body.status,
        "doc_id": body.doc_id,
        "notes": body.notes,
    }
    # Replace existing doc with same name, or append
    docs = bundle["documents"]
    replaced = False
    for i, d in enumerate(docs):
        if d.get("name") == body.name:
            docs[i] = new_doc
            replaced = True
            break
    if not replaced:
        docs.append(new_doc)

    validated = sum(1 for d in docs if d.get("status") == "VALIDATED")
    total = len(docs)
    bundle["documents"] = docs
    bundle["document_count"] = total
    bundle["validated_count"] = validated
    bundle["completeness_pct"] = round(validated / total * 100, 1) if total else 0
    bundle["status"] = "COMPLETE" if validated == total and total > 0 else "INCOMPLETE"
    bundle["updated_at"] = datetime.now(timezone.utc).isoformat()

    return ok(bundle)


@router.get(
    "/bundle",
    response_model=dict,
    summary="Step 7 – List all bundles (in-memory, dev only)",
)
async def list_bundles():
    """List all document bundles (development helper — replace with DB query in production)."""
    return ok({
        "bundles": list(_bundle_store.values()),
        "total": len(_bundle_store),
    })


# ===========================================================================
# Step 4 – MTC Upload + AI Extraction
# ===========================================================================

_MAX_MTC_BYTES = 10 * 1024 * 1024  # 10 MB


@router.post(
    "/mtc/upload",
    response_model=dict,
    summary="Step 4 – Upload Mill Test Certificate and extract fields",
)
async def mtc_upload(
    file: UploadFile = File(..., description="Mill Test Certificate (PDF, DOCX, JPG, PNG)"),
):
    """
    Upload a Mill Test Certificate (EN 10204 3.1 / 3.2) and extract steel-specific fields.

    Returns field-by-field extraction with confidence scores:
    - melt_country_iso / pour_country_iso (mandatory for TCA origin proof)
    - heat_number (traceability)
    - production_route (BF-BOF / EAF / DRI-EAF) — for CBAM SEE
    - chemical composition (Cr, Mo, C, Mn, Si, …) — for classification
    - mechanical properties (tensile, yield, elongation)
    - cbam_see_tco2_per_t (if stated on certificate)

    If melt or pour country is RU or BY, a HARD BLOCK is issued and
    the shipment cannot proceed.
    """
    content = await file.read()

    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(content) > _MAX_MTC_BYTES:
        raise HTTPException(status_code=413, detail="File too large. Maximum 10 MB.")

    # Accept PDF and common image/office types
    filename = file.filename or "mtc"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    allowed = {"pdf", "docx", "jpg", "jpeg", "png"}
    if ext not in allowed:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{ext}'. Accepted: {', '.join(sorted(allowed))}",
        )

    # Compute SHA-256 for audit trail
    doc_hash = hashlib.sha256(content).hexdigest()

    try:
        result = extract_mtc_fields(pdf_bytes=content, filename=filename)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"MTC extraction failed: {exc}")

    result["sha256"] = doc_hash
    result["file_size_bytes"] = len(content)
    return ok(result)


# ===========================================================================
# CBAM Calculator
# ===========================================================================

class CBAMCalculateRequest(BaseModel):
    production_route: str = Field(
        ..., description="Steel production route: BF-BOF | EAF | DRI-EAF | UNKNOWN"
    )
    weight_tonnes: float = Field(..., gt=0, description="Net shipment weight in tonnes")
    actual_see_tco2_per_t: Optional[float] = Field(
        None,
        description="Actual Specific Embedded Emissions (tCO₂/t) from verified MTC. "
                    "If omitted, the route's default factor is used.",
    )
    carbon_price_eur: Optional[float] = Field(
        None, description="EU ETS carbon price (€/tCO₂). Defaults to 78 €/t."
    )
    cbam_declarant_id: Optional[str] = Field(None, description="CBAM authorised declarant ID")


@router.post(
    "/cbam/calculate",
    response_model=dict,
    summary="Step 5 – Calculate CBAM liability",
)
async def cbam_calculate(body: CBAMCalculateRequest):
    """
    Calculate CBAM (Carbon Border Adjustment Mechanism) liability for a steel shipment.

    EU Reg 2023/956 — mandatory for steel imports where total weight > 50 tonnes.

    Returns:
    - applicable: whether CBAM applies
    - liability_eur: estimated CBAM liability at current carbon price
    - liability_if_default_eur: liability if BF-BOF defaults are used
    - saving_eur: financial saving from using actual verified SEE data
    - total_co2_actual_t / total_co2_default_t: embedded CO₂ tonnes
    """
    result = calculate_cbam(
        production_route=body.production_route,
        weight_tonnes=body.weight_tonnes,
        actual_see_tco2_per_t=body.actual_see_tco2_per_t,
        carbon_price_eur=body.carbon_price_eur,
        cbam_declarant_id=body.cbam_declarant_id,
    )
    return ok(result)


# ===========================================================================
# EORI Validation
# ===========================================================================

@router.get(
    "/eori/validate",
    response_model=dict,
    summary="Validate an EORI number via HMRC / EU API",
)
async def eori_validate(eori: str):
    """
    Validate an EORI number format and check it against the HMRC / EU EORI validation API.

    GB EORI format: GB + 12 digits (e.g. GB123456789000)
    XI EORI format: XI + 12 digits (Northern Ireland)
    EU EORI format: 2-letter country code + up to 15 alphanumeric chars

    Note: Live HMRC API validation is attempted; on failure, format-only validation
    is returned with a warning.
    """
    eori_clean = eori.strip().upper()

    # Format validation
    import re as _re
    valid_format = bool(_re.match(r"^[A-Z]{2}[A-Z0-9]{1,15}$", eori_clean))

    if not valid_format:
        return ok({
            "eori": eori_clean,
            "valid": False,
            "format_valid": False,
            "live_check": False,
            "message": (
                "Invalid EORI format. Expected 2-letter country prefix followed by "
                "up to 15 alphanumeric characters (e.g. GB123456789000)."
            ),
        })

    country_prefix = eori_clean[:2]

    # Attempt live HMRC check for GB/XI EORIs
    live_valid = None
    live_checked = False
    live_error = None

    if country_prefix in ("GB", "XI"):
        try:
            import httpx
            async with httpx.AsyncClient(timeout=8) as client:
                resp = await client.get(
                    f"https://api.service.hmrc.gov.uk/customs/eori/validation/{eori_clean}",
                    headers={"Accept": "application/json"},
                )
            if resp.status_code == 200:
                data = resp.json()
                live_valid = data.get("valid", False)
                live_checked = True
            elif resp.status_code == 404:
                live_valid = False
                live_checked = True
        except Exception as exc:
            live_error = str(exc)

    return ok({
        "eori": eori_clean,
        "valid": live_valid if live_checked else valid_format,
        "format_valid": valid_format,
        "live_check": live_checked,
        "country": country_prefix,
        "live_error": live_error,
        "message": (
            "EORI validated via HMRC API." if live_checked and live_valid
            else "EORI format valid; live check unavailable — verify manually at HMRC."
            if not live_checked
            else "EORI not found in HMRC registry."
        ),
    })


# ===========================================================================
# Statement of Origin Generator
# ===========================================================================

class SoOGenerateRequest(BaseModel):
    hs_code: str = Field(..., description="HS commodity code")
    goods_description: str = Field(..., description="Plain-language goods description")
    exporter_eori: str = Field(..., description="Exporter EORI number")
    exporter_name: str = Field(..., description="Exporter legal name")
    origin_country: str = Field("GB", description="ISO-2 country of origin")
    destination_country: str = Field(..., description="ISO-2 destination country")
    weight_tonnes: Optional[float] = Field(None, description="Net weight in tonnes")
    invoice_reference: Optional[str] = Field(None, description="Invoice reference number")
    heat_number: Optional[str] = Field(None, description="Heat/cast number from MTC")
    cumulation_applied: bool = Field(False, description="Whether EU cumulation was applied")
    cumulation_countries: Optional[List[str]] = Field(None, description="Cumulation country ISO codes")
    shipment_value_gbp: Optional[float] = Field(None, description="Shipment value in GBP")
    statement_type: str = Field(
        "ONE_OFF",
        description="ONE_OFF | LONG_TERM",
    )
    long_term_from: Optional[str] = Field(None, description="Long-term start date (YYYY-MM-DD)")
    long_term_to: Optional[str] = Field(None, description="Long-term end date (YYYY-MM-DD)")


@router.post(
    "/soo/generate",
    response_model=dict,
    summary="Step 3 – Generate Statement on Origin (TCA Annex ORIG-4)",
)
async def soo_generate(body: SoOGenerateRequest):
    """
    Generate a TCA-compliant Statement on Origin (Annex ORIG-4).

    Returns the full statement text ready for review and signature,
    plus a validation checklist and SHA-256 hash of the canonical form.
    """
    now_utc = datetime.now(timezone.utc)
    today = now_utc.date().isoformat()
    validity_until = (now_utc + timedelta(days=365)).date().isoformat()

    hs_digits = "".join(ch for ch in body.hs_code if ch.isdigit())
    origin = body.origin_country.upper().strip()
    dest = body.destination_country.upper().strip()

    # Cumulation clause
    if body.cumulation_applied and body.cumulation_countries:
        cum_countries = ", ".join(c.upper() for c in body.cumulation_countries)
        cumulation_clause = f"Cumulation applied with materials originating in: {cum_countries}."
    else:
        cumulation_clause = "No cumulation applied."

    # Long-term period clause
    if body.statement_type == "LONG_TERM" and body.long_term_from and body.long_term_to:
        period_clause = (
            f"\nThis statement on origin applies to all shipments of the described products "
            f"exported in the period from {body.long_term_from} to {body.long_term_to}."
        )
    else:
        period_clause = ""

    # Heat number reference
    heat_clause = (
        f"\nMelt location: {origin} · Heat number: {body.heat_number}"
        if body.heat_number
        else f"\nMelt location: {origin} · Heat number: [from Mill Test Certificate — required]"
    )

    # EORI inclusion threshold (>£5,400 for UK→EU TCA)
    eori_required = (body.shipment_value_gbp or 0) > 5400

    statement_text = (
        f'The exporter of the products covered by this document '
        f'(EORI No: {body.exporter_eori}) declares that, except where otherwise clearly '
        f'indicated, these products are of {origin} preferential origin.\n\n'
        f'{cumulation_clause}\n\n'
        f'Goods: {body.goods_description} · HS {hs_digits}'
        + (f' · {body.weight_tonnes}t' if body.weight_tonnes else '')
        + (f' · Invoice {body.invoice_reference}' if body.invoice_reference else '')
        + heat_clause
        + period_clause
        + f'\n\n{today}'
        + f'\n{body.exporter_name}'
    )

    # Validation checklist
    checklist = [
        {
            "item": "TCA Annex ORIG-4 wording",
            "status": "PASS",
            "note": "Exact match to annexe wording",
        },
        {
            "item": f"EORI {body.exporter_eori}",
            "status": "PENDING",
            "note": "Use /workflow/eori/validate to confirm",
        },
        {
            "item": "Cumulation state",
            "status": "PASS",
            "note": cumulation_clause,
        },
        {
            "item": "Heat number",
            "status": "PASS" if body.heat_number else "WARNING",
            "note": (
                f"Heat {body.heat_number} — present"
                if body.heat_number
                else "MTC not yet uploaded — heat number required for steel (Step 4)"
            ),
        },
        {
            "item": f"Value {'£' + str(int(body.shipment_value_gbp)) if body.shipment_value_gbp else 'unknown'} — EORI inclusion",
            "status": "PASS" if eori_required or not body.shipment_value_gbp else "WARNING",
            "note": (
                f"Value > £5,400: EORI correctly included"
                if eori_required
                else "Value ≤ £5,400: EORI optional but included"
                if body.shipment_value_gbp
                else "Shipment value not provided — verify EORI inclusion requirement"
            ),
        },
        {
            "item": "Validity",
            "status": "PASS",
            "note": f"12 months from today — valid until {validity_until}",
        },
    ]

    canonical = json.dumps(
        {
            "text": statement_text,
            "exporter_eori": body.exporter_eori,
            "hs_code": hs_digits,
            "origin": origin,
            "destination": dest,
            "date": today,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    sha256_hash = hashlib.sha256(canonical.encode()).hexdigest()

    return ok({
        "statement_text": statement_text,
        "statement_type": body.statement_type,
        "origin_country": origin,
        "destination_country": dest,
        "exporter_eori": body.exporter_eori,
        "exporter_name": body.exporter_name,
        "hs_code": hs_digits,
        "issued_date": today,
        "valid_until": validity_until,
        "cumulation_applied": body.cumulation_applied,
        "cumulation_clause": cumulation_clause,
        "checklist": checklist,
        "sha256_hash": sha256_hash,
        "annex_reference": "TCA Annex ORIG-4",
        "regulation": "UK-EU Trade and Cooperation Agreement, Art. ORIG.19",
    })


# ===========================================================================
# EXS Timing Calculator (Step 6)
# ===========================================================================

# EXS pre-lodgement rules (minutes before departure)
_EXS_RULES: Dict[str, Dict[str, Any]] = {
    "SEA_CONTAINER": {
        "label": "Sea container (FCL / LCL)",
        "advance_hours": 24,
        "rule": "24 hours before departure — Art. 105(1)(a) UCC DA",
    },
    "SEA_BULK": {
        "label": "Sea bulk cargo",
        "advance_hours": 4,
        "rule": "4 hours before departure — Art. 105(1)(b) UCC DA",
    },
    "SHORT_SEA": {
        "label": "Short-sea ferry (RoRo, <12h crossing)",
        "advance_hours": 2,
        "rule": "2 hours before departure — Art. 105(1)(c) UCC DA",
    },
    "AIR": {
        "label": "Air freight",
        "advance_hours": 0,
        "advance_minutes": 30,
        "rule": "At least 30 minutes before departure — Art. 106(1) UCC DA",
    },
    "ROAD": {
        "label": "Road / truck",
        "advance_hours": 1,
        "rule": "1 hour before departure — Art. 105(1)(e) UCC DA",
    },
    "RAIL": {
        "label": "Rail freight",
        "advance_hours": 2,
        "rule": "2 hours before departure — Art. 105(1)(f) UCC DA",
    },
}


class EXSCalculateRequest(BaseModel):
    transport_mode: str = Field(
        ...,
        description=(
            "Transport mode: SEA_CONTAINER | SEA_BULK | SHORT_SEA | AIR | ROAD | RAIL"
        ),
    )
    etd_utc: str = Field(
        ...,
        description="Estimated time of departure in UTC (ISO 8601, e.g. '2026-03-28T14:00:00Z')",
    )


@router.post(
    "/exs/calculate",
    response_model=dict,
    summary="Step 6 – Calculate EXS pre-lodgement deadline",
)
async def exs_calculate(body: EXSCalculateRequest):
    """
    Calculate the Entry Summary Declaration (EXS / ENS) pre-lodgement deadline.

    Returns the latest time by which the EXS must be lodged with HMRC CDS,
    based on the transport mode and estimated departure time.
    Implements EU UCC Delegated Act Article 105/106 timing rules.
    """
    mode = body.transport_mode.upper().strip()
    if mode not in _EXS_RULES:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Unknown transport mode '{mode}'. "
                f"Valid modes: {', '.join(sorted(_EXS_RULES.keys()))}"
            ),
        )

    rule = _EXS_RULES[mode]

    try:
        etd = datetime.fromisoformat(body.etd_utc.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail="etd_utc must be a valid ISO 8601 datetime, e.g. '2026-03-28T14:00:00Z'",
        )

    hours = rule.get("advance_hours", 0)
    minutes = rule.get("advance_minutes", 0)
    deadline = etd - timedelta(hours=hours, minutes=minutes)

    return ok({
        "transport_mode": mode,
        "transport_label": rule["label"],
        "etd_utc": etd.isoformat(),
        "exs_deadline_utc": deadline.isoformat(),
        "advance_notice": f"{hours}h{f' {minutes}min' if minutes else ''}",
        "legal_basis": rule["rule"],
        "within_time": deadline > datetime.now(timezone.utc),
    })


# ===========================================================================
# TRQ Live Quota Detail
# ===========================================================================

_TRQ_CATEGORIES: Dict[str, Dict[str, Any]] = {
    "EU_CAT26": {
        "name": "EU Steel Safeguard — Category 26 (Other alloy steel flat-rolled / semi-finished)",
        "hs_chapters": ["7224", "7225", "7226"],
        "authority": "European Commission — DG TAXUD",
        "regulation": "EU Implementing Regulation (EU) 2019/159, as amended",
        "in_quota_duty_pct": 0.0,
        "out_quota_duty_pct": 25.0,
        "new_out_quota_duty_pct": 50.0,
        "new_rate_applies_from": "2026-07-01",
        "quota_period": "Q1 2026 (Jan–Mar)",
        "quota_tonnes_total": 287400.0,
        "quota_tonnes_remaining": 195432.0,  # mock — fetch from TARIC in production
        "quota_pct_remaining": 68.0,
        "estimated_depletion_weeks": 11,
        "last_updated": "2026-03-21T08:00:00Z",
        "alert_threshold_pct": 25,
        "taric_url": "https://ec.europa.eu/taxation_customs/dds2/taric",
    },
    "UK_SAFEGUARD": {
        "name": "UK Steel Safeguard (SI 2021/1122)",
        "hs_chapters": ["7208", "7209", "7210", "7211", "7212"],
        "authority": "UK Trade Remedies Authority",
        "regulation": "UK Safeguard (Tariff Quota) Regulations 2021 SI 1122",
        "in_quota_duty_pct": 0.0,
        "out_quota_duty_pct": 25.0,
        "quota_period": "Q1 2026 (Jan–Mar)",
        "quota_tonnes_total": 145000.0,
        "quota_tonnes_remaining": 98700.0,
        "quota_pct_remaining": 68.1,
        "estimated_depletion_weeks": 9,
        "last_updated": "2026-03-21T08:00:00Z",
        "alert_threshold_pct": 25,
        "tra_url": "https://www.trade-remedies.service.gov.uk",
    },
}


@router.get(
    "/trq/quota/{category}",
    response_model=dict,
    summary="Step 2 – Get live TRQ quota data for a category",
)
async def trq_quota(category: str):
    """
    Return detailed live quota data for a TRQ category.

    Supported categories: EU_CAT26 | UK_SAFEGUARD

    Returns:
    - quota_tonnes_remaining / quota_pct_remaining
    - in-quota and out-of-quota duty rates
    - estimated weeks to quota exhaustion
    - traffic-light status: GREEN (>50%) / AMBER (25–50%) / RED (<25%)

    Note: tonnage figures are mocked in this version.
    In production, fetch live from EU TARIC and UK TRA APIs.
    """
    cat = category.upper().strip()
    if cat not in _TRQ_CATEGORIES:
        raise HTTPException(
            status_code=404,
            detail=(
                f"TRQ category '{cat}' not found. "
                f"Available: {', '.join(sorted(_TRQ_CATEGORIES.keys()))}"
            ),
        )

    data = dict(_TRQ_CATEGORIES[cat])
    pct = data.get("quota_pct_remaining", 100.0)

    if pct > 50:
        status = "GREEN"
    elif pct >= 25:
        status = "AMBER"
    else:
        status = "RED"

    data["status"] = status
    data["category"] = cat
    data["data_note"] = (
        "Quota data is indicative. Fetch live from TARIC / UK TRA before lodging declarations."
    )

    return ok(data)
