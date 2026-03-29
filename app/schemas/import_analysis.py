"""
Pydantic v2 schemas for the Import Analysis API.

All request and response models live here so that services, adapters, and
routers all import from a single canonical location.
"""
from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------

class ImportAnalysisRequest(BaseModel):
    """Body accepted by POST /api/v1/import-analysis."""

    product_description: str = Field(
        ...,
        min_length=3,
        max_length=2000,
        description="Plain-language description of the goods being imported.",
        examples=["Men's woven cotton trousers"],
    )
    origin_country: str = Field(
        ...,
        min_length=2,
        max_length=2,
        description="ISO 3166-1 alpha-2 country of origin.",
        examples=["CN"],
    )
    destination_country: str = Field(
        ...,
        min_length=2,
        max_length=2,
        description="ISO 3166-1 alpha-2 destination (importing) country.",
        examples=["DE"],
    )
    customs_value: Optional[float] = Field(
        None,
        gt=0,
        description="Transaction value of the goods (ex-freight unless incoterms imply otherwise).",
    )
    currency: str = Field(
        "EUR",
        min_length=3,
        max_length=3,
        description="ISO 4217 currency code for all monetary fields.",
    )
    freight: Optional[float] = Field(None, ge=0, description="Freight cost to destination.")
    insurance: Optional[float] = Field(None, ge=0, description="Insurance cost.")
    quantity: Optional[float] = Field(None, gt=0, description="Quantity of goods.")
    quantity_unit: Optional[str] = Field(None, max_length=20, description="Unit of measure (pcs, kg, m², …).")
    incoterms: Optional[str] = Field(None, max_length=10, description="Incoterms code (EXW, FOB, CIF, DAP, …).")
    manufacturer_name: Optional[str] = Field(None, description="Optional manufacturer for anti-dumping lookups.")
    goods_description_extended: Optional[str] = Field(
        None, description="Technical specification or additional detail beyond the product description."
    )

    @field_validator("origin_country", "destination_country", mode="before")
    @classmethod
    def uppercase_iso(cls, v: str) -> str:
        return str(v).strip().upper()

    @field_validator("currency", mode="before")
    @classmethod
    def uppercase_currency(cls, v: str) -> str:
        return str(v).strip().upper()


# ---------------------------------------------------------------------------
# Internal data-transfer objects (not exposed in the API response directly)
# ---------------------------------------------------------------------------

class HSClassificationRaw(BaseModel):
    """Raw JSON output from the OpenAI classification call (before enrichment)."""

    primary_hs_code: str
    confidence: float = Field(ge=0.0, le=1.0)
    alternative_hs_codes: list[str]
    reasoning_summary: str
    missing_attributes: list[str]


class TariffData(BaseModel):
    """Output of the tariff adapter for a given (hs_code, origin, destination) triple."""

    duty_rate: Optional[float]                         # MFN ad-valorem duty %
    anti_dumping: bool = False
    anti_dumping_rate: Optional[float] = None          # % if applicable
    countervailing: bool = False
    countervailing_rate: Optional[float] = None
    excise: bool = False
    excise_rate: Optional[float] = None
    other_measures: list[dict[str, Any]] = Field(default_factory=list)
    documents_required: list[str] = Field(default_factory=list)
    tariff_notes: list[str] = Field(default_factory=list)


class VATData(BaseModel):
    """Output of the VAT adapter for a given (destination, hs_code) pair."""

    vat_rate: Optional[float]                          # Standard import VAT %
    vat_category: str = "STANDARD"                     # STANDARD | REDUCED | ZERO | EXEMPT
    vat_notes: list[str] = Field(default_factory=list)


class OriginRulesResult(BaseModel):
    """Output of the origin rules service."""

    preferential_eligible: bool
    preferential_duty_rate: Optional[float]
    agreement_name: Optional[str] = None
    proof_of_origin_required: Optional[str] = None    # e.g. "EUR.1", "REX", "Statement on Origin"
    notes: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------

class HSClassificationResult(BaseModel):
    """Public-facing HS classification block in the API response."""

    primary_hs_code: str = Field(description="Most likely HS code (6+ digits).")
    confidence: float = Field(ge=0.0, le=1.0, description="AI confidence in the primary code (0–1).")
    alternative_hs_codes: list[str] = Field(description="Other plausible codes in descending likelihood.")
    reasoning_summary: str = Field(description="Short plain-language explanation of the classification.")
    missing_attributes: list[str] = Field(
        description="Product attributes that, if provided, would increase confidence."
    )
    review_required: bool = Field(
        description="True when confidence is below the configured threshold."
    )


class RatesResult(BaseModel):
    duty_rate: Optional[float] = Field(None, description="MFN import duty rate (%).")
    effective_duty_rate: Optional[float] = Field(
        None, description="Effective duty rate (%) including stacked additional duties (safeguard/anti-dumping) when applicable."
    )
    vat_rate: Optional[float] = Field(None, description="Import VAT / import tax rate (%).")
    preferential_duty_rate: Optional[float] = Field(
        None, description="Preferential duty rate (%) if the origin qualifies."
    )
    preferential_eligible: bool = Field(description="Whether preferential origin treatment applies.")
    preferential_agreement: Optional[str] = Field(None, description="Name of the applicable trade agreement.")


class MeasuresResult(BaseModel):
    anti_dumping: bool
    anti_dumping_rate: Optional[float] = None
    countervailing: bool
    countervailing_rate: Optional[float] = None
    excise: bool
    excise_rate: Optional[float] = None
    other_measures: list[dict[str, Any]] = Field(default_factory=list)


class ComplianceResult(BaseModel):
    documents_required: list[str]
    notes: list[str]


class CalculationResult(BaseModel):
    cif_value: Optional[float] = Field(None, description="Cost + Insurance + Freight value used as duty basis.")
    duty_amount: Optional[float] = Field(None, description="Calculated duty in the request currency.")
    vat_amount: Optional[float] = Field(None, description="Calculated VAT/import tax in the request currency.")
    total_landed_cost: Optional[float] = Field(None, description="cif_value + duty + VAT.")
    currency: Optional[str] = None
    duty_basis: str = Field(description="Explanation of what the duty was calculated on.")
    vat_basis: str = Field(description="Explanation of what VAT was calculated on.")


class SourceRecord(BaseModel):
    type: str
    provider: str
    model: Optional[str] = None


class ImportAnalysisResponse(BaseModel):
    """Full API response envelope."""

    success: bool
    input: ImportAnalysisRequest
    classification: HSClassificationResult
    rates: RatesResult
    measures: MeasuresResult
    compliance: ComplianceResult
    calculation: CalculationResult
    sources: list[SourceRecord]
    tariff_lookup: Optional[dict[str, Any]] = Field(
        None,
        description="Raw tariff lookup report used for the calculation (same shape as /api/v1/tariff/lookup data).",
    )
