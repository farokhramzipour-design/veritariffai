"""
Monetary calculation utilities for import cost estimation.

All amounts are in the currency provided by the caller — no FX conversion
is performed here. For multi-currency support, plug in an FX adapter.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class LandedCostBreakdown:
    """Structured result from calculate_landed_cost()."""

    cif_value: float
    duty_rate_pct: float
    duty_amount: float
    vat_rate_pct: float
    vat_basis: float
    vat_amount: float
    total_landed_cost: float
    currency: str
    duty_basis_note: str
    vat_basis_note: str


def calculate_cif(
    *,
    customs_value: float,
    freight: Optional[float],
    insurance: Optional[float],
    incoterms: Optional[str],
) -> float:
    """
    Derive the CIF (Cost + Insurance + Freight) value used as the duty basis.

    - If incoterms is already CIF or CIP, the customs_value is taken as-is.
    - Otherwise, freight and insurance are added to customs_value.
    """
    inco = (incoterms or "").upper()
    if inco in ("CIF", "CIP"):
        # Value already includes cost, insurance, and freight
        return customs_value

    cif = customs_value
    if freight:
        cif += freight
    if insurance:
        cif += insurance
    return cif


def calculate_landed_cost(
    *,
    customs_value: float,
    freight: Optional[float],
    insurance: Optional[float],
    incoterms: Optional[str],
    duty_rate_pct: float,
    vat_rate_pct: float,
    currency: str = "EUR",
    destination_uses_cif_plus_duty_for_vat: bool = True,
) -> LandedCostBreakdown:
    """
    Calculate duty, VAT, and total landed cost.

    Args:
        customs_value:   Transaction / invoice value of goods.
        freight:         Freight cost (added to CIF if incoterms is not CIF/CIP).
        insurance:       Insurance cost.
        incoterms:       Trade term (EXW, FOB, CIF, DAP, etc.).
        duty_rate_pct:   Ad-valorem duty rate in percent (e.g. 12.0).
        vat_rate_pct:    Import VAT rate in percent (e.g. 19.0).
        currency:        ISO 4217 currency code.
        destination_uses_cif_plus_duty_for_vat:
                         Most jurisdictions (EU, UK) apply VAT on CIF + duty.
                         Set False for jurisdictions that apply VAT on CIF only.

    Returns:
        LandedCostBreakdown with all intermediate values.
    """
    cif = calculate_cif(
        customs_value=customs_value,
        freight=freight,
        insurance=insurance,
        incoterms=incoterms,
    )

    duty_amount = round(cif * duty_rate_pct / 100, 2)

    if destination_uses_cif_plus_duty_for_vat:
        vat_basis = cif + duty_amount
        vat_basis_note = "CIF value + import duty"
    else:
        vat_basis = cif
        vat_basis_note = "CIF value only"

    vat_amount = round(vat_basis * vat_rate_pct / 100, 2)
    total = round(cif + duty_amount + vat_amount, 2)

    return LandedCostBreakdown(
        cif_value=round(cif, 2),
        duty_rate_pct=duty_rate_pct,
        duty_amount=duty_amount,
        vat_rate_pct=vat_rate_pct,
        vat_basis=round(vat_basis, 2),
        vat_amount=vat_amount,
        total_landed_cost=total,
        currency=currency,
        duty_basis_note="CIF value (customs_value + freight + insurance where applicable)",
        vat_basis_note=vat_basis_note,
    )
