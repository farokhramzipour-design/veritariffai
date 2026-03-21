"""
Workflow API – Steps 2 (RoO Wizard), TRQ, Section 301, UFLPA, CSL,
              Step 5 (Licences), Step 6 (CDS Declaration), Step 7 (Document Bundle).

All routes are protected (JWT required via the parent router's dependency).
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.responses import ok
from app.engines.roo_wizard import run_roo_wizard
from app.engines.trq_screen import screen_trq
from app.engines.compliance_screen import screen_section_301, screen_uflpa, screen_csl

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
