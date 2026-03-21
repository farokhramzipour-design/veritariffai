"""
Compliance Screening engine – Section 301, UFLPA, and CSL/Entity List.

Three sub-engines:

1. Section 301 (US-China tariff)
   - Identifies the tariff list (1 / 2 / 3 / 4A / 4B) for the HS code
   - Calculates the additional Section 301 duty rate (7.5% or 25%)
   - Checks for active exclusions (placeholder – USTR exclusion list)

2. UFLPA Clean Supply Chain Audit
   - Screens factory/supplier address for Xinjiang geographic risk
   - Maps sub-tier supplier risk
   - Returns rebuttable-presumption status

3. CSL / Entity List screening
   - Screens party names against the OFAC SDN list (placeholder)
   - Screens against US BIS Entity List
   - Screens against ITA Consolidated Screening List (CSL)

In production, these should call:
  - USTR Section 301 exclusions API / Federal Register
  - US BIS Entity List API
  - ITA CSL API  (https://api.trade.gov/consolidated_screening_list/)
  - OFAC SDN API (https://sanctionslist.ofac.treas.gov/)
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Section 301 – US-China tariff lists
# ---------------------------------------------------------------------------

# Each entry: (hs6_prefix_or_range, list_name, additional_rate_pct)
# Source: USTR Section 301 Actions (Lists 1–4B), 19 CFR Part 2640
_SECTION_301_LISTS: List[Dict[str, Any]] = [
    # List 1 – industrial machinery & components (25%)
    {"prefix": "8471", "list": "List 1", "rate_pct": 25.0,
     "description": "Automatic data processing machines"},
    {"prefix": "8473", "list": "List 1", "rate_pct": 25.0,
     "description": "Parts for ADP machines"},
    {"prefix": "8479", "list": "List 1", "rate_pct": 25.0,
     "description": "Machines for specific industries"},
    # List 2 – chemicals & materials (25%)
    {"prefix": "2902", "list": "List 2", "rate_pct": 25.0,
     "description": "Cyclic hydrocarbons"},
    {"prefix": "3926", "list": "List 2", "rate_pct": 25.0,
     "description": "Other articles of plastics"},
    # List 3 – broad manufactured goods (25%)
    {"prefix": "7208", "list": "List 3", "rate_pct": 25.0,
     "description": "Flat-rolled iron/steel (hot-rolled)"},
    {"prefix": "7209", "list": "List 3", "rate_pct": 25.0,
     "description": "Flat-rolled iron/steel (cold-rolled)"},
    {"prefix": "7210", "list": "List 3", "rate_pct": 25.0,
     "description": "Flat-rolled iron/steel (coated)"},
    {"prefix": "7214", "list": "List 3", "rate_pct": 25.0,
     "description": "Bars and rods of iron or steel"},
    {"prefix": "7216", "list": "List 3", "rate_pct": 25.0,
     "description": "Angles, shapes, sections"},
    {"prefix": "7217", "list": "List 3", "rate_pct": 25.0,
     "description": "Wire of iron or non-alloy steel"},
    {"prefix": "7219", "list": "List 3", "rate_pct": 25.0,
     "description": "Flat-rolled stainless steel (hot)"},
    {"prefix": "7220", "list": "List 3", "rate_pct": 25.0,
     "description": "Flat-rolled stainless steel (cold)"},
    {"prefix": "7224", "list": "List 3", "rate_pct": 25.0,
     "description": "Semi-finished products of alloy steel"},
    {"prefix": "7225", "list": "List 3", "rate_pct": 25.0,
     "description": "Flat-rolled alloy steel"},
    {"prefix": "7226", "list": "List 3", "rate_pct": 25.0,
     "description": "Flat-rolled stainless/alloy (narrow)"},
    {"prefix": "7228", "list": "List 3", "rate_pct": 25.0,
     "description": "Bars/rods of alloy steel"},
    # List 4A – consumer electronics (7.5%)
    {"prefix": "8517", "list": "List 4A", "rate_pct": 7.5,
     "description": "Telephone sets & smartphones"},
    {"prefix": "8528", "list": "List 4A", "rate_pct": 7.5,
     "description": "Monitors and projectors"},
    # List 4B – remaining goods (15% → stayed at 7.5%)
    {"prefix": "6110", "list": "List 4B", "rate_pct": 7.5,
     "description": "Jerseys, pullovers (knitted)"},
    {"prefix": "6201", "list": "List 4B", "rate_pct": 7.5,
     "description": "Men's overcoats"},
]

# Placeholder exclusions – USTR grants exclusions via Federal Register notices
# Production should load these from the USTR exclusions database.
_ACTIVE_EXCLUSIONS: List[str] = [
    "8471.30",  # example exclusion on portable ADP machines
]


def screen_section_301(
    *,
    hs_code: str,
    origin_country: str,
    destination_country: str,
    customs_value_usd: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Screen for US Section 301 (China tariff) applicability.

    Only applicable when origin_country == CN and destination_country == US.
    """
    warnings: List[str] = []
    origin = origin_country.upper().strip()
    dest = destination_country.upper().strip()
    hs_digits = "".join(ch for ch in hs_code if ch.isdigit())
    hs6 = hs_digits[:6] if len(hs_digits) >= 6 else hs_digits
    hs4 = hs_digits[:4] if len(hs_digits) >= 4 else hs_digits

    if origin != "CN" or dest != "US":
        return {
            "applicable": False,
            "reason": f"Section 301 applies to CN→US trade only. Route: {origin}→{dest}.",
            "warnings": [],
        }

    matched: Optional[Dict[str, Any]] = None
    for entry in _SECTION_301_LISTS:
        prefix = entry["prefix"]
        if hs6.startswith(prefix) or hs4 == prefix[:4]:
            matched = entry
            break

    if not matched:
        return {
            "applicable": False,
            "reason": f"HS code {hs_code} not found on Section 301 tariff lists (Lists 1–4B).",
            "warnings": warnings,
        }

    # Check exclusions
    exclusion_active = any(
        hs6.startswith(excl.replace(".", "")) or hs_code.startswith(excl)
        for excl in _ACTIVE_EXCLUSIONS
    )

    additional_duty_usd: Optional[float] = None
    if customs_value_usd is not None:
        additional_duty_usd = round(customs_value_usd * matched["rate_pct"] / 100, 2)

    if exclusion_active:
        warnings.append(
            f"An active USTR exclusion may apply to HS {hs_code}. "
            "Verify the exclusion is still valid at ustr.gov before claiming."
        )

    return {
        "applicable": True,
        "tariff_list": matched["list"],
        "hs_description": matched["description"],
        "additional_duty_rate_pct": matched["rate_pct"],
        "additional_duty_usd": additional_duty_usd,
        "exclusion_active": exclusion_active,
        "exclusion_note": (
            "Active USTR exclusion found — duty may be waived. Confirm at ustr.gov."
            if exclusion_active else None
        ),
        "action": (
            f"Additional Section 301 duty of {matched['rate_pct']}% applies to {hs_code} "
            f"({matched['description']}) imported from China. "
            "Declare on US CBP Form 7501 under HTS classification with applicable duty."
        ),
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# UFLPA – Uyghur Forced Labor Prevention Act
# ---------------------------------------------------------------------------

# High-risk Xinjiang geography prefixes (city, region, prefecture names)
_XINJIANG_KEYWORDS = {
    "xinjiang", "xuar", "uyghur", "urumqi", "kashgar", "hotan", "aksu",
    "turpan", "hami", "bayingol", "ili", "changji", "karamay", "tacheng",
    "altay", "kizilsu", "yili",
}

# Sectors with elevated UFLPA risk (UFLPA Entity List sectors)
_HIGH_RISK_SECTORS = {
    "cotton", "polysilicon", "tomatoes", "ppg", "textile", "solar",
    "aluminium", "aluminum", "steel",
}

# Placeholder UFLPA entity list (production: load from CBP/DHS)
_UFLPA_ENTITIES: List[str] = [
    "Xinjiang Production and Construction Corps",
    "XPCC",
    "Hoshine Silicon",
    "Daqo New Energy",
]


def _name_in_uflpa(name: str) -> Optional[str]:
    name_lower = name.lower()
    for entity in _UFLPA_ENTITIES:
        if entity.lower() in name_lower:
            return entity
    return None


def _has_xinjiang_risk(address: str) -> bool:
    addr_lower = address.lower()
    return any(kw in addr_lower for kw in _XINJIANG_KEYWORDS)


def screen_uflpa(
    *,
    factory_name: Optional[str] = None,
    factory_address: Optional[str] = None,
    supplier_names: Optional[List[str]] = None,
    goods_description: Optional[str] = None,
    hs_code: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run the UFLPA supply chain audit.

    Returns a rebuttable_presumption flag and risk factors found.
    """
    warnings: List[str] = []
    risk_factors: List[Dict[str, str]] = []
    rebuttable_presumption = False

    all_names = list(filter(None, [factory_name] + (supplier_names or [])))

    # Check entity list
    for name in all_names:
        entity = _name_in_uflpa(name)
        if entity:
            rebuttable_presumption = True
            risk_factors.append({
                "type": "UFLPA_ENTITY_LIST",
                "severity": "BLOCK",
                "detail": (
                    f"'{name}' matches UFLPA Entity List entry '{entity}'. "
                    "Goods from this entity are presumed to be made with forced labor. "
                    "Importation into the US is prohibited unless the importer rebuts "
                    "this presumption with clear and convincing evidence."
                ),
            })

    # Check Xinjiang address
    address_combined = " ".join(filter(None, [factory_address]))
    if address_combined and _has_xinjiang_risk(address_combined):
        rebuttable_presumption = True
        risk_factors.append({
            "type": "XINJIANG_GEOGRAPHY",
            "severity": "HIGH",
            "detail": (
                "Factory address contains Xinjiang geographic identifiers. "
                "Under UFLPA, goods from the Xinjiang Uyghur Autonomous Region (XUAR) "
                "are subject to a rebuttable presumption of forced-labor production."
            ),
        })

    # Sector risk
    if goods_description:
        desc_lower = goods_description.lower()
        for sector in _HIGH_RISK_SECTORS:
            if sector in desc_lower:
                risk_factors.append({
                    "type": "HIGH_RISK_SECTOR",
                    "severity": "WARNING",
                    "detail": (
                        f"Goods description references '{sector}', a sector identified "
                        "by DHS as having elevated UFLPA risk. Enhanced due diligence required."
                    ),
                })
                warnings.append(
                    f"'{sector}' sector goods require enhanced supply chain documentation "
                    "under UFLPA. Maintain traceability records for all sub-tier suppliers."
                )
                break

    # Sub-tier supplier warnings
    if supplier_names and len(supplier_names) > 3:
        warnings.append(
            f"{len(supplier_names)} sub-tier suppliers identified. "
            "Ensure supplier declarations and traceability records are maintained for all tiers."
        )

    if rebuttable_presumption:
        warnings.append(
            "UFLPA rebuttable presumption applies. To import into the US, the importer must "
            "provide clear and convincing evidence that goods were not produced with forced labor. "
            "Contact CBP's EADM team for guidance."
        )

    return {
        "rebuttable_presumption": rebuttable_presumption,
        "risk_factors": risk_factors,
        "factory_name": factory_name,
        "factory_address": factory_address,
        "supplier_names_checked": len(all_names),
        "action": (
            "Obtain supplier attestations, traceability documentation, and third-party "
            "audit reports for all tiers of the supply chain."
            if rebuttable_presumption else
            "No UFLPA flags found. Maintain standard supply chain records."
        ),
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# CSL / Entity List Screening
# ---------------------------------------------------------------------------

# Placeholder CSL data (production: query ITA CSL API)
_CSL_ENTRIES: List[Dict[str, str]] = [
    {"name": "Huawei Technologies", "list": "BIS Entity List",
     "country": "CN", "programs": "EAR"},
    {"name": "ZTE Corporation", "list": "BIS Entity List",
     "country": "CN", "programs": "EAR"},
    {"name": "Hikvision", "list": "BIS Entity List",
     "country": "CN", "programs": "EAR"},
    {"name": "Dahua Technology", "list": "BIS Entity List",
     "country": "CN", "programs": "EAR"},
    {"name": "Rosoboronexport", "list": "OFAC SDN",
     "country": "RU", "programs": "RUSSIA-EO"},
    {"name": "Russian Federal Security Service", "list": "OFAC SDN",
     "country": "RU", "programs": "RUSSIA-EO"},
]


def _fuzzy_match(query: str, candidate: str) -> bool:
    """Very lightweight fuzzy match: all words of query in candidate."""
    q_words = re.split(r"\W+", query.lower())
    c_lower = candidate.lower()
    return all(w in c_lower for w in q_words if len(w) >= 3)


def screen_csl(
    *,
    party_names: List[str],
    party_countries: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Screen party names against ITA CSL / BIS Entity List / OFAC SDN.

    Returns a list of hits with the matching list and recommended action.
    """
    warnings: List[str] = []
    hits: List[Dict[str, Any]] = []
    countries = [c.upper() for c in (party_countries or [])]

    for name in party_names:
        for entry in _CSL_ENTRIES:
            if _fuzzy_match(name, entry["name"]):
                # Country filter: if countries provided, only match same country
                if countries and entry["country"] not in countries:
                    continue
                hits.append({
                    "party_name": name,
                    "matched_entry": entry["name"],
                    "list": entry["list"],
                    "country": entry["country"],
                    "programs": entry["programs"],
                    "severity": "BLOCK",
                    "action": (
                        f"'{name}' matches '{entry['name']}' on the {entry['list']}. "
                        "Proceeding with this transaction may violate US export control law (EAR) "
                        "or OFAC sanctions regulations. Obtain legal advice before proceeding."
                    ),
                })

    cleared = len(hits) == 0

    if hits:
        warnings.append(
            f"{len(hits)} CSL/Entity List match(es) found. "
            "Transaction is BLOCKED pending legal review."
        )

    return {
        "cleared": cleared,
        "hits": hits,
        "parties_checked": party_names,
        "action": (
            "Transaction cleared — no CSL/Entity List matches found."
            if cleared else
            "Transaction BLOCKED. Review hits and obtain legal advice before proceeding."
        ),
        "warnings": warnings,
    }
