"""
TRQ (Tariff Rate Quota) Live Screening engine.

Screens a shipment against:
  - EU Steel Safeguard Category 26 quotas (EC Regulation 2019/159 as amended)
  - UK Steel Safeguard quotas (SI 2021/1122)
  - Generic TRQ flags for other Chapter 72/73 subheadings

Returns a GREEN / AMBER / RED quota status with quota details.

In production the quota fill-rates should be fetched from:
  - EU: TARIC consultation / DG TAXUD API
  - UK: HMRC Trade Tariff API  (https://api.trade-tariff.service.gov.uk/)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Static quota catalogue  (replace with live API calls in production)
# ---------------------------------------------------------------------------

# EU Category 26 – flat steel products originating from third countries
# Fill rate thresholds: GREEN < 80%, AMBER 80–99%, RED ≥ 100%
_EU_CATEGORY_26 = {
    "category": "EU Category 26",
    "regulation": "EC Reg 2019/159 (as amended by 2021/1351, 2022/664, 2023/369)",
    "description": "Flat-rolled products of iron / non-alloy steel (HS 7208–7212)",
    "hs_prefixes": {"7208", "7209", "7210", "7211", "7212"},
    "quota_fill_pct": 62.0,   # placeholder — fetch from DG TAXUD in production
    "in_quota_rate": "0%",
    "out_of_quota_rate": "25%",
    "quota_period": "Q4 2025",
}

# UK safeguard categories for steel Chapter 72
_UK_STEEL_CATEGORIES = [
    {
        "category": "UK Steel Safeguard – Category 1",
        "regulation": "UK Global Tariff, SI 2021/1122",
        "description": "Hot-rolled flat products (HS 7208, 7211)",
        "hs_prefixes": {"7208", "7211"},
        "quota_fill_pct": 55.0,
        "in_quota_rate": "0%",
        "out_of_quota_rate": "25%",
        "quota_period": "Q4 2025",
    },
    {
        "category": "UK Steel Safeguard – Category 5",
        "regulation": "UK Global Tariff, SI 2021/1122",
        "description": "Cold-rolled flat products (HS 7209, 7210)",
        "hs_prefixes": {"7209", "7210"},
        "quota_fill_pct": 88.0,
        "in_quota_rate": "0%",
        "out_of_quota_rate": "25%",
        "quota_period": "Q4 2025",
    },
    {
        "category": "UK Steel Safeguard – Category 13",
        "regulation": "UK Global Tariff, SI 2021/1122",
        "description": "Stainless hot-rolled flat products (HS 7219, 7220)",
        "hs_prefixes": {"7219", "7220"},
        "quota_fill_pct": 34.0,
        "in_quota_rate": "0%",
        "out_of_quota_rate": "25%",
        "quota_period": "Q4 2025",
    },
    {
        "category": "UK Steel Safeguard – Category 16",
        "regulation": "UK Global Tariff, SI 2021/1122",
        "description": "Rebar (HS 7214)",
        "hs_prefixes": {"7214"},
        "quota_fill_pct": 97.0,
        "in_quota_rate": "0%",
        "out_of_quota_rate": "25%",
        "quota_period": "Q4 2025",
    },
]

_AMBER_THRESHOLD = 80.0
_RED_THRESHOLD = 100.0


def _quota_status(fill_pct: float) -> str:
    if fill_pct >= _RED_THRESHOLD:
        return "RED"
    elif fill_pct >= _AMBER_THRESHOLD:
        return "AMBER"
    return "GREEN"


def _status_detail(status: str, fill_pct: float, out_rate: str) -> str:
    if status == "GREEN":
        return f"Quota is open ({fill_pct:.1f}% filled). In-quota rate applies."
    elif status == "AMBER":
        return (
            f"Quota is nearly exhausted ({fill_pct:.1f}% filled). "
            f"Risk of out-of-quota duty ({out_rate}) if filled before arrival. "
            "Secure allocation early."
        )
    else:
        return (
            f"Quota exhausted ({fill_pct:.1f}% filled). "
            f"Out-of-quota duty rate {out_rate} applies. "
            "Consider delaying shipment to next quota period."
        )


# ---------------------------------------------------------------------------
# Public entry-point
# ---------------------------------------------------------------------------

def screen_trq(
    *,
    hs_code: str,
    origin_country: str,
    destination_country: str,
    shipment_weight_kg: Optional[float] = None,
    shipment_value_gbp: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Screen a shipment against applicable TRQs and return quota status.

    Returns:
        trq_applicable   : bool
        matches          : list of matching quota records with status
        overall_status   : GREEN | AMBER | RED | NOT_APPLICABLE
        warnings         : list[str]
    """
    warnings: List[str] = []
    matches: List[Dict[str, Any]] = []

    hs_digits = "".join(ch for ch in hs_code if ch.isdigit())
    hs6 = hs_digits[:6] if len(hs_digits) >= 6 else hs_digits
    hs4 = hs_digits[:4] if len(hs_digits) >= 4 else hs_digits
    chapter = hs_digits[:2] if len(hs_digits) >= 2 else ""

    dest = destination_country.upper().strip()
    origin = origin_country.upper().strip()

    _EU_COUNTRIES = {
        "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR",
        "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL",
        "PL", "PT", "RO", "SK", "SI", "ES", "SE",
    }

    # -----------------------------------------------------------------------
    # EU Category 26 (destination is an EU member state)
    # -----------------------------------------------------------------------
    if dest in _EU_COUNTRIES:
        cat = _EU_CATEGORY_26
        for prefix in cat["hs_prefixes"]:
            if hs6.startswith(prefix) or hs4.startswith(prefix[:4]):
                fill = cat["quota_fill_pct"]
                status = _quota_status(fill)
                matches.append({
                    "jurisdiction": "EU",
                    "category": cat["category"],
                    "regulation": cat["regulation"],
                    "description": cat["description"],
                    "quota_period": cat["quota_period"],
                    "quota_fill_pct": fill,
                    "in_quota_rate": cat["in_quota_rate"],
                    "out_of_quota_rate": cat["out_of_quota_rate"],
                    "status": status,
                    "status_detail": _status_detail(status, fill, cat["out_of_quota_rate"]),
                    "action": (
                        "Verify current quota balance at DG TAXUD TARIC before shipment. "
                        "Quote order number on the EU import declaration."
                    ),
                })
                break

    # -----------------------------------------------------------------------
    # UK Safeguard (destination is GB)
    # -----------------------------------------------------------------------
    if dest in ("GB", "UK"):
        for cat in _UK_STEEL_CATEGORIES:
            for prefix in cat["hs_prefixes"]:
                if hs6.startswith(prefix) or hs4.startswith(prefix[:4]):
                    fill = cat["quota_fill_pct"]
                    status = _quota_status(fill)
                    matches.append({
                        "jurisdiction": "UK",
                        "category": cat["category"],
                        "regulation": cat["regulation"],
                        "description": cat["description"],
                        "quota_period": cat["quota_period"],
                        "quota_fill_pct": fill,
                        "in_quota_rate": cat["in_quota_rate"],
                        "out_of_quota_rate": cat["out_of_quota_rate"],
                        "status": status,
                        "status_detail": _status_detail(status, fill, cat["out_of_quota_rate"]),
                        "action": (
                            "Check current quota balance at HMRC Trade Tariff. "
                            "Declare the correct quota order number on the CDS import entry."
                        ),
                    })
                    break

    # -----------------------------------------------------------------------
    # Generic Chapter 72/73 advisory
    # -----------------------------------------------------------------------
    if not matches and chapter in ("72", "73"):
        warnings.append(
            f"HS code {hs_code} (Chapter {chapter}) may be subject to additional "
            "TRQ or safeguard measures. Verify at the relevant national tariff portal."
        )

    trq_applicable = bool(matches)

    # Overall status: worst across all matches
    if not matches:
        overall_status = "NOT_APPLICABLE"
    elif any(m["status"] == "RED" for m in matches):
        overall_status = "RED"
    elif any(m["status"] == "AMBER" for m in matches):
        overall_status = "AMBER"
    else:
        overall_status = "GREEN"

    if overall_status == "RED":
        warnings.append(
            "One or more TRQs are EXHAUSTED. Out-of-quota duty rates will apply. "
            "Consider delaying shipment to the next quota period."
        )
    elif overall_status == "AMBER":
        warnings.append(
            "One or more TRQs are near exhaustion. Secure your quota allocation "
            "immediately to avoid out-of-quota duties."
        )

    return {
        "trq_applicable": trq_applicable,
        "overall_status": overall_status,
        "matches": matches,
        "hs_code": hs_code,
        "origin_country": origin,
        "destination_country": dest,
        "warnings": warnings,
    }
