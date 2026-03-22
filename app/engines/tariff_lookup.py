"""
UK Trade Tariff commodity lookup engine.

Fetches live data from:
  https://www.trade-tariff.service.gov.uk/uk/api/commodities/{hs_code}

Extracts for a given origin → GB destination:
  - VAT rate
  - MFN (third-country) duty rate
  - Preferential duty rate (if origin has a trade agreement with UK)
  - Additional/surcharge duties (e.g. Russia/Belarus +35%)
  - Import controls and licence requirements
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

_BASE_URL = "https://www.trade-tariff.service.gov.uk/uk/api/commodities"
_TIMEOUT = 15  # seconds

# Measure type IDs used by the UK Trade Tariff
_MT_THIRD_COUNTRY = "103"          # MFN duty
_MT_TARIFF_PREF = "142"            # Tariff preference (trade agreement)
_MT_ADDITIONAL = "551"             # Additional duty (retaliatory / sanctions)
_MT_SUSPENSION = "115"             # Autonomous suspension
_MT_END_USE = "106"                # End-use relief
_MT_ANTIDUMPING = "552"            # Anti-dumping
_MT_COUNTERVAILING = "672"         # Countervailing

# Country groups that map a single ISO code to a tariff group ID used in the API
_COUNTRY_GROUPS: dict[str, list[str]] = {
    "EU": [
        "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR",
        "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL",
        "PL", "PT", "RO", "SK", "SI", "ES", "SE",
    ],
    "1006": ["CH"],   # Switzerland group in HMRC
    "1008": ["NO"],   # Norway group
    "1011": [         # EU + EEA group sometimes used
        "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR",
        "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL",
        "PL", "PT", "RO", "SK", "SI", "ES", "SE", "IS", "LI", "NO",
    ],
}


def _groups_for_country(iso2: str) -> set[str]:
    """Return all group IDs that include this country ISO code."""
    groups = {iso2}
    for group_id, members in _COUNTRY_GROUPS.items():
        if iso2 in members:
            groups.add(group_id)
    return groups


def _parse_pct(text: str | None) -> float | None:
    """Extract a numeric percentage from strings like '<span>2.00</span> %'."""
    if not text:
        return None
    m = re.search(r"([\d.]+)\s*%", text)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            return None
    return None


def _build_index(included: list[dict]) -> dict[str, dict[str, dict]]:
    """
    Build a lookup: index[type][id] = resource_object
    so we can resolve relationships quickly.
    """
    index: dict[str, dict[str, dict]] = {}
    for obj in included:
        t = obj.get("type", "")
        i = obj.get("id", "")
        if t and i:
            index.setdefault(t, {})[i] = obj
    return index


async def lookup_commodity(
    hs_code: str,
    origin_country: str,
    destination_country: str,
) -> dict[str, Any]:
    """
    Fetch the HMRC UK Trade Tariff commodity endpoint and return a structured
    duty + VAT summary tailored to the origin → destination route.

    Args:
        hs_code:            10-digit commodity code (digits only).
        origin_country:     ISO-2 country of origin.
        destination_country: ISO-2 destination (only GB/UK fully supported).

    Returns:
        dict with keys: hs_code, description, vat_pct, mfn_duty_pct,
        applicable_duty_pct, duty_type, preferential, additional_duties,
        controls, warnings, source.
    """
    origin = origin_country.upper().strip()
    dest = destination_country.upper().strip()
    hs = "".join(ch for ch in hs_code if ch.isdigit())

    warnings: list[str] = []
    controls: list[dict] = []

    if dest not in ("GB", "UK"):
        warnings.append(
            f"Destination '{dest}' is not GB — live duty data is only available "
            "for UK imports. Results may not be accurate."
        )

    # ------------------------------------------------------------------
    # Fetch from HMRC API
    # ------------------------------------------------------------------
    url = f"{_BASE_URL}/{hs}"
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                url,
                params={"currency": "GBP"},
                headers={"Accept": "application/json"},
            )
        resp.raise_for_status()
        payload = resp.json()
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            return _error_result(hs_code, origin, dest, f"Commodity {hs_code} not found in UK Trade Tariff.")
        return _error_result(hs_code, origin, dest, f"HMRC API error {exc.response.status_code}.")
    except Exception as exc:
        logger.exception("HMRC API fetch failed for %s", hs)
        return _error_result(hs_code, origin, dest, f"Failed to reach HMRC API: {exc}")

    data = payload.get("data", {})
    included = payload.get("included", [])
    meta = payload.get("meta", {})

    index = _build_index(included)

    # ------------------------------------------------------------------
    # Commodity description
    # ------------------------------------------------------------------
    attrs = data.get("attributes", {})
    description = attrs.get("formatted_description") or attrs.get("description", "")

    # ------------------------------------------------------------------
    # VAT — from meta.duty_calculator.applicable_vat_options
    # ------------------------------------------------------------------
    vat_pct: float | None = None
    vat_label: str | None = None
    dc = meta.get("duty_calculator", {})
    vat_opts = dc.get("applicable_vat_options", {})
    for label, text in vat_opts.items():
        pct = _parse_pct(text)
        if pct is not None:
            vat_pct = pct
            vat_label = text
            break

    # ------------------------------------------------------------------
    # MFN duty — from import_trade_summary (basic_third_country_duty)
    # ------------------------------------------------------------------
    mfn_pct: float | None = None
    ts_rel = data.get("relationships", {}).get("import_trade_summary", {}).get("data", {})
    if ts_rel:
        ts_obj = index.get("import_trade_summary", {}).get(ts_rel.get("id", ""), {})
        mfn_raw = ts_obj.get("attributes", {}).get("basic_third_country_duty")
        mfn_pct = _parse_pct(mfn_raw)

    # ------------------------------------------------------------------
    # Walk import measures to find origin-specific rates
    # ------------------------------------------------------------------
    measure_ids = [
        m["id"]
        for m in data.get("relationships", {}).get("import_measures", {}).get("data", [])
    ]
    measures = [index.get("measure", {}).get(mid, {}) for mid in measure_ids if mid in index.get("measure", {})]

    origin_groups = _groups_for_country(origin)

    preferential_pct: float | None = None
    additional_duties: list[dict] = []

    for measure in measures:
        m_attrs = measure.get("attributes", {})
        m_rels = measure.get("relationships", {})

        mt_id = (m_rels.get("measure_type", {}).get("data") or {}).get("id", "")
        geo_id = (m_rels.get("geographical_area", {}).get("data") or {}).get("id", "")
        duty_expr_id = (m_rels.get("duty_expression", {}).get("data") or {}).get("id", "")

        # Only consider measures that apply to this origin country/group
        if geo_id and geo_id not in origin_groups and geo_id != "1011":
            # "1011" is sometimes used as "all countries" group — keep it
            continue

        duty_expr = index.get("duty_expression", {}).get(duty_expr_id, {})
        rate_text = duty_expr.get("attributes", {}).get("base", "")
        rate_pct = _parse_pct(rate_text)

        if mt_id == _MT_TARIFF_PREF:
            # Take the best (lowest) preferential rate
            if rate_pct is not None:
                if preferential_pct is None or rate_pct < preferential_pct:
                    mt_obj = index.get("measure_type", {}).get(mt_id, {})
                    mt_desc = mt_obj.get("attributes", {}).get("description", "Tariff preference")
                    preferential_pct = rate_pct

        elif mt_id in (_MT_ADDITIONAL, _MT_ANTIDUMPING, _MT_COUNTERVAILING):
            mt_obj = index.get("measure_type", {}).get(mt_id, {})
            mt_desc = mt_obj.get("attributes", {}).get("description", "Additional duty")
            if rate_pct is not None:
                additional_duties.append({
                    "type": mt_desc,
                    "rate_pct": rate_pct,
                    "rate_text": rate_text,
                    "geographical_area": geo_id,
                })

        elif mt_id in (_MT_SUSPENSION, _MT_END_USE):
            mt_obj = index.get("measure_type", {}).get(mt_id, {})
            mt_desc = mt_obj.get("attributes", {}).get("description", "Suspension")
            controls.append({
                "type": "SUSPENSION",
                "description": mt_desc,
                "rate_pct": rate_pct,
                "rate_text": rate_text,
            })

    # ------------------------------------------------------------------
    # Determine the applicable duty rate for this origin
    # ------------------------------------------------------------------
    if preferential_pct is not None:
        applicable_duty_pct = preferential_pct
        duty_type = "PREFERENTIAL"
    elif mfn_pct is not None:
        applicable_duty_pct = mfn_pct
        duty_type = "MFN"
    else:
        applicable_duty_pct = None
        duty_type = "UNKNOWN"
        warnings.append("Could not determine duty rate. Check the HMRC Trade Tariff manually.")

    # ------------------------------------------------------------------
    # Sanctions advisory
    # ------------------------------------------------------------------
    if origin in ("RU", "BY"):
        warnings.append(
            f"Goods originating in {origin} may be subject to additional UK sanctions measures. "
            "Verify the current applicable duty and import prohibition status."
        )
    if origin == "KP":
        warnings.append("Imports from North Korea (KP) are prohibited under UK sanctions.")

    # ------------------------------------------------------------------
    # Total landed duty estimate (excluding VAT)
    # ------------------------------------------------------------------
    total_duty_pct: float | None = None
    if applicable_duty_pct is not None:
        total_duty_pct = applicable_duty_pct + sum(d["rate_pct"] for d in additional_duties)

    return {
        "hs_code": hs,
        "description": description,
        "origin_country": origin,
        "destination_country": dest,
        # Duty
        "mfn_duty_pct": mfn_pct,
        "preferential_duty_pct": preferential_pct,
        "applicable_duty_pct": applicable_duty_pct,
        "duty_type": duty_type,
        "additional_duties": additional_duties,
        "total_duty_pct": total_duty_pct,
        # VAT
        "vat_pct": vat_pct,
        "vat_label": vat_label,
        # Suspensions / end-use reliefs
        "controls": controls,
        "warnings": warnings,
        "source": "UK Trade Tariff (live)",
        "source_url": f"https://www.trade-tariff.service.gov.uk/commodities/{hs}",
    }


def _error_result(hs_code: str, origin: str, dest: str, message: str) -> dict:
    return {
        "hs_code": hs_code,
        "description": None,
        "origin_country": origin,
        "destination_country": dest,
        "mfn_duty_pct": None,
        "preferential_duty_pct": None,
        "applicable_duty_pct": None,
        "duty_type": "UNKNOWN",
        "additional_duties": [],
        "total_duty_pct": None,
        "vat_pct": None,
        "vat_label": None,
        "controls": [],
        "warnings": [message],
        "source": "UK Trade Tariff (live)",
        "source_url": f"https://www.trade-tariff.service.gov.uk/commodities/{hs_code}",
    }
