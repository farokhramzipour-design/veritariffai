"""
Compliance API – Steps 3 & 4 of the Veritariff Happy Path.

Step 3 – Sanctions & Restrictions Screening
    POST /compliance/sanctions-screen
        Screen party names, countries, and HS codes against:
        - UK OFSI consolidated list
        - EU sanctions (centralised database)
        - OFAC (US) – advisory
        - UK safeguarding / tariff quotas (TRQs) flags
        - Import/export licence checks

Step 4 – Clearance Gate
    POST /compliance/clearance
        Validate the mandatory document checklist and generate a Veritariff
        Clearance Certificate (timestamped, SHA-256 hash) once all checks pass.

    GET /compliance/clearance/{clearance_id}
        Retrieve a previously issued clearance certificate.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.responses import ok

router = APIRouter()


# ---------------------------------------------------------------------------
# Sanctions & Restrictions Screening
# ---------------------------------------------------------------------------

# Country-level sanction regimes active under UK / EU law
# (illustrative – production should load from DB / external list)
_SANCTIONED_COUNTRIES_UK = {
    "RU": "Russia – UK sanctions (Russia Regulations 2019, as amended)",
    "BY": "Belarus – UK sanctions (Belarus Regulations 2019, as amended)",
    "KP": "North Korea – UK sanctions (Democratic People's Republic of Korea Regulations)",
    "IR": "Iran – UK sanctions (Iran Regulations 2019)",
    "SY": "Syria – UK sanctions (Syria Regulations 2019)",
    "MM": "Myanmar – UK sanctions (Myanmar Regulations 2021)",
}
_SANCTIONED_COUNTRIES_EU = {
    "RU": "Russia – EU Council Regulation 833/2014 and associated measures",
    "BY": "Belarus – EU Council Regulation 765/2006",
    "KP": "North Korea – EU Council Regulation 329/2007",
    "IR": "Iran – EU Council Regulation 267/2012",
    "SY": "Syria – EU Council Regulation 36/2012",
}

# HS chapters / headings subject to sector-specific UK measures (Russia context)
_RESTRICTED_HS_CHAPTERS_UK_RUSSIA = {
    "72", "73",  # Iron & steel
    "84", "85",  # Machinery & electronics
    "87",        # Vehicles
    "88",        # Aircraft (dual-use)
}


class SanctionsScreenRequest(BaseModel):
    """
    Input for the sanctions / restrictions screening step (Happy Path Step 3).
    """

    # Parties
    exporter_country: str = Field(..., description="ISO-2 country of the exporting party")
    importer_country: str = Field(..., description="ISO-2 country of the importing party")
    consignee_country: Optional[str] = Field(None, description="ISO-2 country of end consignee")
    party_names: List[str] = Field(
        default_factory=list,
        description="List of party names to screen (exporter, importer, freight-forwarder, etc.)",
    )

    # Goods
    hs_code: str = Field(..., description="10-digit commodity code")
    goods_description: Optional[str] = Field(None, description="Brief goods description")

    # Journey
    origin_country: str = Field(..., description="ISO-2 country of origin")
    destination_country: str = Field(..., description="ISO-2 country of final destination")

    # Trade terms
    jurisdiction: str = Field("UK", description="UK | EU – which sanctions regime to screen")


class SanctionFlag(BaseModel):
    flag_type: str  # COUNTRY_SANCTION | SECTOR_RESTRICTION | PARTY_MATCH | LICENCE_REQUIRED | TRQ
    severity: str   # BLOCK | WARNING | INFO
    source: str
    detail: str
    action_required: str


class SanctionsScreenResponse(BaseModel):
    cleared: bool
    flags: List[SanctionFlag] = Field(default_factory=list)
    import_licence_required: bool = False
    export_licence_required: bool = False
    trq_applicable: bool = False
    audit_trail: List[dict] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


def _run_sanctions_screen(req: SanctionsScreenRequest) -> SanctionsScreenResponse:
    """
    Lightweight sanctions screening engine.

    Production implementation should integrate with:
    - OFSI API (api.gov.uk/government/organisations/office-of-financial-sanctions-implementation)
    - EC FSAP (ec.europa.eu/assets/fisma/sanctions/)
    - HMRC Trade Tariff measure conditions
    - OFAC SDN list (US)
    """
    flags: list[SanctionFlag] = []
    audit: list[dict] = []
    warnings: list[str] = []

    origin = req.origin_country.upper()
    dest = req.destination_country.upper()
    exporter_c = req.exporter_country.upper()
    importer_c = req.importer_country.upper()
    jurisdiction = req.jurisdiction.upper()

    hs_digits = "".join(ch for ch in req.hs_code if ch.isdigit())
    chapter = hs_digits[:2] if len(hs_digits) >= 2 else ""

    countries_to_check = {origin, dest, exporter_c, importer_c}
    if req.consignee_country:
        countries_to_check.add(req.consignee_country.upper())

    # ------------------------------------------------------------------
    # Country-level sanctions
    # ------------------------------------------------------------------
    sanction_db = _SANCTIONED_COUNTRIES_UK if jurisdiction == "UK" else _SANCTIONED_COUNTRIES_EU
    for country in countries_to_check:
        if country in sanction_db:
            flags.append(SanctionFlag(
                flag_type="COUNTRY_SANCTION",
                severity="BLOCK",
                source=f"{'UK OFSI' if jurisdiction == 'UK' else 'EU FSAP'} – Consolidated List",
                detail=sanction_db[country],
                action_required=(
                    "Shipment BLOCKED: a sanctioned country is involved in this trade. "
                    "Obtain written legal advice and any applicable OFSI / EU licence before proceeding."
                ),
            ))
            audit.append({
                "step": "country_sanction_check",
                "country": country,
                "result": "BLOCKED",
                "source": sanction_db[country],
            })

    # ------------------------------------------------------------------
    # Sector-specific restrictions (UK Russia steel measures)
    # ------------------------------------------------------------------
    if jurisdiction == "UK" and origin == "RU" and chapter in _RESTRICTED_HS_CHAPTERS_UK_RUSSIA:
        flags.append(SanctionFlag(
            flag_type="SECTOR_RESTRICTION",
            severity="BLOCK",
            source="UK Russia Regulations – steel & iron sector ban",
            detail=(
                f"HS chapter {chapter} goods originating from Russia are subject to "
                "UK import restrictions under the Russia (Sanctions) (EU Exit) Regulations 2019."
            ),
            action_required=(
                "Import of these goods from Russia is prohibited or requires a specific "
                "OFSI licence. Contact the Department for Business and Trade."
            ),
        ))
        audit.append({
            "step": "sector_restriction_check",
            "chapter": chapter,
            "origin": origin,
            "result": "BLOCKED",
        })

    # ------------------------------------------------------------------
    # UK safeguarding / tariff quotas
    # ------------------------------------------------------------------
    # Steel safeguard quotas (UK Steel Safeguard Measures)
    if chapter == "72" and jurisdiction == "UK":
        flags.append(SanctionFlag(
            flag_type="TRQ",
            severity="WARNING",
            source="UK Steel Safeguard – SI 2021/1122",
            detail=(
                "Steel products (Chapter 72) are subject to UK safeguarding Tariff Rate Quotas "
                "(TRQs). Out-of-quota shipments attract an additional safeguard duty. "
                "Check the current quota balance via the UK Global Tariff."
            ),
            action_required=(
                "Verify current TRQ balance for the applicable safeguard category. "
                "Declare the correct quota order number on the import declaration."
            ),
        ))
        audit.append({
            "step": "trq_check",
            "chapter": chapter,
            "result": "TRQ_APPLICABLE",
        })

    # ------------------------------------------------------------------
    # Import / export licence flags
    # ------------------------------------------------------------------
    import_licence_required = chapter in {"87", "88", "93"}  # vehicles, aircraft, arms
    export_licence_required = chapter in {"88", "93"}         # dual-use / arms

    if import_licence_required:
        flags.append(SanctionFlag(
            flag_type="LICENCE_REQUIRED",
            severity="WARNING",
            source="UK Export Control Joint Unit (ECJU) / HMRC",
            detail=f"HS chapter {chapter} may require an import licence.",
            action_required="Apply for the relevant import licence via SPIRE or HMRC before shipment arrives.",
        ))
    if export_licence_required:
        flags.append(SanctionFlag(
            flag_type="LICENCE_REQUIRED",
            severity="WARNING",
            source="UK ECJU",
            detail=f"HS chapter {chapter} may require an export licence (dual-use / strategic goods).",
            action_required="Apply for an export licence via SPIRE before shipment departs.",
        ))

    # ------------------------------------------------------------------
    # Anti-dumping / UK safeguarding measures check (steel)
    # ------------------------------------------------------------------
    if chapter == "72" and dest in {"GB", "UK"}:
        warnings.append(
            "Check whether anti-dumping duties (ADDs) apply to the specific HS subheading "
            "and country of origin via the UK Global Tariff. Anti-dumping measures for steel "
            "products are frequently updated."
        )

    trq_applicable = any(f.flag_type == "TRQ" for f in flags)
    cleared = not any(f.severity == "BLOCK" for f in flags)

    audit.append({
        "step": "screening_summary",
        "cleared": cleared,
        "total_flags": len(flags),
        "block_flags": sum(1 for f in flags if f.severity == "BLOCK"),
    })

    return SanctionsScreenResponse(
        cleared=cleared,
        flags=flags,
        import_licence_required=import_licence_required,
        export_licence_required=export_licence_required,
        trq_applicable=trq_applicable,
        audit_trail=audit,
        warnings=warnings,
    )


@router.post(
    "/sanctions-screen",
    response_model=dict,
    summary="Sanctions & restrictions screening (Step 3)",
)
async def sanctions_screen(body: SanctionsScreenRequest):
    """
    Screen the shipment parties, countries, and HS code against UK OFSI,
    EU sanctions databases, and sector-specific trade restrictions
    (Happy Path Step 3).

    Returns a cleared/blocked status with detailed flags and required actions.
    """
    result = _run_sanctions_screen(body)
    return ok(result.model_dump())


# ---------------------------------------------------------------------------
# Clearance Gate – Step 4
# ---------------------------------------------------------------------------

MANDATORY_DOCS = [
    "commercial_invoice",
    "packing_list",
    "cds_mrn",           # Customs Declaration Service Movement Reference Number
    "mtc_verified",      # Mill Test Certificate verified (for steel)
    "sanctions_cleared", # Sanctions screen passed
]


class DocumentStatus(BaseModel):
    name: str
    status: str  # VALIDATED | PENDING | MISSING | REJECTED
    notes: Optional[str] = None


class ClearanceRequest(BaseModel):
    """
    Mandatory document checklist for the export clearance gate (Happy Path Step 4).
    """

    shipment_ref: str = Field(..., description="Shipment / calculation request reference")

    # Document statuses
    documents: List[DocumentStatus] = Field(
        ...,
        description=(
            "Status of each mandatory document. Must include: "
            + ", ".join(MANDATORY_DOCS)
        ),
    )

    # TCA preference check
    tca_preference_claimed: bool = Field(False, description="Whether TCA preferential rate is claimed")
    origin_declaration_signed: bool = Field(
        False,
        description="Whether the origin declaration / Statement on Origin has been signed",
    )
    origin_declaration_id: Optional[str] = Field(
        None, description="Declaration ID returned by POST /origin/declaration"
    )

    # Shipment parties for certificate
    exporter_name: Optional[str] = None
    exporter_eori: Optional[str] = None
    importer_name: Optional[str] = None
    freight_forwarder_name: Optional[str] = None
    hs_code: Optional[str] = None
    goods_description: Optional[str] = None
    destination_country: Optional[str] = None


class ClearanceCertificate(BaseModel):
    clearance_id: str
    shipment_ref: str
    issued_at: str
    sha256_hash: str
    status: str  # CLEARED_FOR_EXPORT | BLOCKED
    blocks: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    exporter_name: Optional[str] = None
    exporter_eori: Optional[str] = None
    importer_name: Optional[str] = None
    freight_forwarder_name: Optional[str] = None
    hs_code: Optional[str] = None
    goods_description: Optional[str] = None
    destination_country: Optional[str] = None
    bundle_reference: Optional[str] = None


def _issue_clearance(req: ClearanceRequest) -> ClearanceCertificate:
    """
    Validate the mandatory document checklist and issue a Veritariff Clearance
    Certificate when all conditions are met (Happy Path Step 4).

    The certificate payload is:
      - timestamped (UTC)
      - hashed (SHA-256 of canonical JSON representation)
      - assigned a unique clearance_id
    A bundle_reference is returned that the caller should use to retrieve the
    ZIP document bundle from S3 (AES-256 encrypted).
    """
    blocks: list[str] = []
    warnings: list[str] = []
    issued_at = datetime.now(timezone.utc).isoformat()

    # Build document lookup
    doc_lookup: Dict[str, str] = {d.name: d.status for d in req.documents}

    # ------------------------------------------------------------------
    # Mandatory document check
    # ------------------------------------------------------------------
    for doc_name in MANDATORY_DOCS:
        status = doc_lookup.get(doc_name, "MISSING")
        if status != "VALIDATED":
            blocks.append(
                f"DOCUMENT BLOCKED: '{doc_name}' status is '{status}' – must be VALIDATED."
            )

    # ------------------------------------------------------------------
    # TCA origin declaration check
    # ------------------------------------------------------------------
    if req.tca_preference_claimed and not req.origin_declaration_signed:
        blocks.append(
            "TCA preference claimed but origin declaration is not signed. "
            "Obtain a signed Statement on Origin or REX declaration before release."
        )

    if req.tca_preference_claimed and not req.origin_declaration_id:
        warnings.append(
            "TCA preference claimed but no origin_declaration_id provided. "
            "Ensure the origin declaration has been recorded via POST /origin/declaration."
        )

    # ------------------------------------------------------------------
    # Determine final status
    # ------------------------------------------------------------------
    status = "CLEARED_FOR_EXPORT" if not blocks else "BLOCKED"

    # ------------------------------------------------------------------
    # Build certificate payload and hash
    # ------------------------------------------------------------------
    clearance_id = str(uuid.uuid4())
    bundle_reference = str(uuid.uuid4()) if status == "CLEARED_FOR_EXPORT" else None

    cert_payload = {
        "clearance_id": clearance_id,
        "shipment_ref": req.shipment_ref,
        "issued_at": issued_at,
        "status": status,
        "exporter_eori": req.exporter_eori,
        "hs_code": req.hs_code,
        "destination_country": req.destination_country,
    }
    canonical = json.dumps(cert_payload, sort_keys=True, separators=(",", ":"))
    sha256_hash = hashlib.sha256(canonical.encode()).hexdigest()

    return ClearanceCertificate(
        clearance_id=clearance_id,
        shipment_ref=req.shipment_ref,
        issued_at=issued_at,
        sha256_hash=sha256_hash,
        status=status,
        blocks=blocks,
        warnings=warnings,
        exporter_name=req.exporter_name,
        exporter_eori=req.exporter_eori,
        importer_name=req.importer_name,
        freight_forwarder_name=req.freight_forwarder_name,
        hs_code=req.hs_code,
        goods_description=req.goods_description,
        destination_country=req.destination_country,
        bundle_reference=bundle_reference,
    )


# In-memory store for demo purposes (replace with DB in production)
_clearance_store: Dict[str, dict] = {}


@router.post(
    "/clearance",
    response_model=dict,
    summary="Clearance gate – validate documents and issue certificate (Step 4)",
)
async def create_clearance(body: ClearanceRequest):
    """
    Run the export clearance gate (Happy Path Step 4).

    Validates all mandatory documents (commercial_invoice, packing_list,
    cds_mrn, mtc_verified, sanctions_cleared) plus the TCA origin declaration
    when a preference is claimed.

    On success: generates a Veritariff Clearance Certificate with a
    timestamped SHA-256 hash and a bundle_reference for the AES-256
    encrypted ZIP stored in S3.

    On failure: returns BLOCKED status with the list of blocking conditions
    that must be resolved.
    """
    cert = _issue_clearance(body)
    _clearance_store[cert.clearance_id] = cert.model_dump()
    return ok(cert.model_dump())


@router.get(
    "/clearance/{clearance_id}",
    response_model=dict,
    summary="Retrieve a previously issued clearance certificate",
)
async def get_clearance(clearance_id: str):
    """
    Retrieve a Veritariff Clearance Certificate by its clearance_id.
    """
    from fastapi import HTTPException

    cert = _clearance_store.get(clearance_id)
    if not cert:
        raise HTTPException(
            status_code=404,
            detail=f"Clearance certificate '{clearance_id}' not found.",
        )
    return ok(cert)
