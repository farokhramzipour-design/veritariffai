"""
CBAM (Carbon Border Adjustment Mechanism) calculator engine.

EU Regulation 2023/956 — mandatory for steel imports >50t threshold.

Calculates:
  - Specific Embedded Emissions (SEE) actual vs BF-BOF default
  - CBAM liability = total_tCO2 × carbon_price_eur_per_t
  - Savings vs using default emissions factors
"""

from __future__ import annotations

from typing import Any

# Default BF-BOF emissions factors (tCO₂/t of steel) — EU CBAM Annex III
_DEFAULT_EMISSIONS: dict[str, float] = {
    "BF-BOF": 1.987,          # Blast Furnace – Basic Oxygen Furnace
    "EAF": 0.493,             # Electric Arc Furnace (default, if no actual data)
    "DRI-EAF": 0.641,         # Direct Reduced Iron – EAF
    "UNKNOWN": 1.987,         # Conservative: assume BF-BOF
}

# EU ETS carbon price (€/tCO₂) — placeholder; in production fetch from live API
_DEFAULT_CARBON_PRICE_EUR = 78.0

# CBAM threshold for steel (tonnes)
_CBAM_THRESHOLD_T = 50.0


def calculate_cbam(
    *,
    production_route: str,
    weight_tonnes: float,
    actual_see_tco2_per_t: float | None = None,
    carbon_price_eur: float | None = None,
    cbam_declarant_id: str | None = None,
) -> dict[str, Any]:
    """
    Calculate CBAM liability for a steel shipment.

    Args:
        production_route:      "BF-BOF" | "EAF" | "DRI-EAF" | "UNKNOWN"
        weight_tonnes:         Net weight of steel in tonnes.
        actual_see_tco2_per_t: Actual Specific Embedded Emissions (tCO₂/t)
                               from the Mill Test Certificate / verifier report.
                               If None, the default for the route is used.
        carbon_price_eur:      EU ETS carbon price (€/tCO₂).  Defaults to 78.
        cbam_declarant_id:     Optional CBAM declarant identifier.

    Returns:
        dict with fields: applicable, route, weight_tonnes, actual_see, default_see,
        total_co2_actual, total_co2_default, carbon_price, liability_eur,
        liability_if_default_eur, saving_eur, threshold_t, warnings.
    """
    route = production_route.upper().strip()
    if route not in _DEFAULT_EMISSIONS:
        route = "UNKNOWN"

    carbon_price = carbon_price_eur if carbon_price_eur is not None else _DEFAULT_CARBON_PRICE_EUR
    default_see = _DEFAULT_EMISSIONS[route]

    # Use actual SEE if provided (verified data); otherwise use route default
    if actual_see_tco2_per_t is not None:
        see_used = actual_see_tco2_per_t
        using_actual = True
    else:
        see_used = default_see
        using_actual = False

    applicable = weight_tonnes > _CBAM_THRESHOLD_T

    total_co2_actual = round(weight_tonnes * see_used, 4)
    total_co2_default = round(weight_tonnes * default_see, 4)

    liability_eur = round(total_co2_actual * carbon_price, 2)
    liability_if_default_eur = round(total_co2_default * carbon_price, 2)
    saving_eur = round(liability_if_default_eur - liability_eur, 2)

    warnings: list[str] = []
    if not applicable:
        warnings.append(
            f"Shipment weight {weight_tonnes}t is below the CBAM threshold of "
            f"{_CBAM_THRESHOLD_T}t. CBAM reporting is not mandatory for this shipment."
        )
    if not using_actual:
        warnings.append(
            "No actual SEE data provided — default emissions factor used. "
            "Upload a verified Mill Test Certificate to reduce CBAM liability."
        )
    if route == "UNKNOWN":
        warnings.append(
            "Production route could not be determined. "
            "Conservative BF-BOF default applied — actual liability may be lower."
        )

    return {
        "applicable": applicable,
        "production_route": route,
        "weight_tonnes": weight_tonnes,
        "threshold_tonnes": _CBAM_THRESHOLD_T,
        # Emissions
        "actual_see_tco2_per_t": see_used if using_actual else None,
        "default_see_tco2_per_t": default_see,
        "see_used_tco2_per_t": see_used,
        "using_actual_see": using_actual,
        "total_co2_actual_t": total_co2_actual,
        "total_co2_default_t": total_co2_default,
        # Financials
        "carbon_price_eur_per_t": carbon_price,
        "liability_eur": liability_eur,
        "liability_if_default_eur": liability_if_default_eur,
        "saving_eur": max(saving_eur, 0.0),
        # Admin
        "cbam_declarant_id": cbam_declarant_id,
        "first_surrender_deadline": "2027-09-30",
        "regulation": "EU Reg 2023/956",
        "warnings": warnings,
    }
