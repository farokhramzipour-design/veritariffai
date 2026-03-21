"""
Rules of Origin Wizard – Gates 1 through 3F.

Implements the full TCA/preferential origin decision tree:

  Gate 1  – MFN Gateway (is a preferential agreement in play?)
  Gate 2  – Document completeness check
  Gate 3A – Wholly Obtained test
  Gate 3B – Product-Specific Rule / Change of Tariff Heading (PSR/CTH)
  Gate 3C – Cumulation (bilateral, diagonal, full)
  Gate 3D – Sufficient Processing / Regional Value Content (RVC)
  Gate 3E – Final origin determination
  Gate 3F – Statement-of-Origin (SoO) generation
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Trade agreement registry
# ---------------------------------------------------------------------------

# Agreements the UK currently operates
_UK_AGREEMENTS: Dict[str, Dict[str, Any]] = {
    "UK-EU-TCA": {
        "name": "UK-EU Trade and Cooperation Agreement (SR 2020/1432)",
        "parties": "GB",
        "partner_countries": {
            "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR",
            "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL",
            "PL", "PT", "RO", "SK", "SI", "ES", "SE",
        },
        "default_rvc_threshold": 50.0,
        "soo_text_template": (
            "The exporter of the products covered by this document "
            "(Exporter Reference: {exporter_ref}) declares that, "
            "except where otherwise clearly indicated, these products are of "
            "{origin_country} preferential origin."
        ),
        "high_value_threshold_gbp": 6000,
        "high_value_declaration": "REX_DECLARATION",
        "low_value_declaration": "STATEMENT_ON_ORIGIN",
    },
    "UKGTS": {
        "name": "UK Generalised Trade Scheme",
        "parties": "GB",
        "partner_countries": set(),  # populated from GSP beneficiaries – omitted for brevity
        "default_rvc_threshold": 50.0,
        "soo_text_template": (
            "The exporter declares that these goods originate in {origin_country} "
            "and satisfy the rules of origin of the UK Generalised Trade Scheme."
        ),
        "high_value_threshold_gbp": 6000,
        "high_value_declaration": "REX_DECLARATION",
        "low_value_declaration": "STATEMENT_ON_ORIGIN",
    },
}

# Chapter-level PSR notes (illustrative – Annex ORIG-2 of the UK-EU TCA)
_PSR_NOTES: Dict[str, str] = {
    "72": (
        "Chapter 72 (iron & steel): TCA Annex ORIG-2 generally requires manufacture from "
        "materials of any heading (CTH rule). Specific subheadings may require further "
        "processing. Verify the applicable PSR in TCA Annex ORIG-2."
    ),
    "73": (
        "Chapter 73 (articles of iron or steel): CTH rule applies; some subheadings "
        "additionally require an RVC ≥ 45% or a specific chemical/processing step."
    ),
    "84": (
        "Chapter 84 (machinery): CTH or CTSH rule depending on subheading; some "
        "require RVC ≥ 50%."
    ),
    "85": (
        "Chapter 85 (electrical machinery): CTH rule common; value-added thresholds "
        "vary by subheading."
    ),
    "87": (
        "Chapter 87 (vehicles): Strict PSR – minimum 55% regional value content from "
        "originating materials for passenger cars."
    ),
}


# ---------------------------------------------------------------------------
# Result dataclasses (plain dicts for JSON serialisation)
# ---------------------------------------------------------------------------

def _gate(name: str, result: str, detail: str) -> Dict[str, str]:
    return {"gate": name, "result": result, "detail": detail}


# ---------------------------------------------------------------------------
# Public entry-point
# ---------------------------------------------------------------------------

def run_roo_wizard(
    *,
    hs_code: str,
    origin_country: str,
    destination_country: str,
    # Gate 3A
    wholly_obtained: bool = False,
    # Gate 3B
    materials_hs_codes: Optional[List[str]] = None,
    ctsh_satisfied: Optional[bool] = None,
    # Gate 3C
    cumulation_countries: Optional[List[str]] = None,
    # Gate 3D
    regional_value_content_pct: Optional[float] = None,
    non_originating_value: Optional[float] = None,
    ex_works_price: Optional[float] = None,
    # Gate 3F
    exporter_ref: Optional[str] = None,
    shipment_value_gbp: Optional[float] = None,
    # Documents
    documents_provided: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Run the full RoO wizard (Gates 1–3F).

    Returns a result dict with keys:
      origin_status        : WHOLLY_OBTAINED | SUFFICIENT_PROCESSING |
                             INSUFFICIENT_PROCESSING | UNKNOWN
      origin_qualified     : bool
      agreement            : str | None
      declaration_type     : STATEMENT_ON_ORIGIN | REX_DECLARATION | NONE
      soo_text             : str | None
      gates                : list[dict]  – per-gate audit trail
      warnings             : list[str]
    """
    gates: List[Dict[str, str]] = []
    warnings: List[str] = []

    origin = origin_country.upper().strip()
    dest = destination_country.upper().strip()
    hs_digits = "".join(ch for ch in hs_code if ch.isdigit())
    chapter = hs_digits[:2] if len(hs_digits) >= 2 else ""
    hs6 = hs_digits[:6] if len(hs_digits) >= 6 else hs_digits
    docs = [d.lower().strip() for d in (documents_provided or [])]

    # -----------------------------------------------------------------------
    # Gate 1 – MFN Gateway: is a preferential agreement available?
    # -----------------------------------------------------------------------
    agreement_key: Optional[str] = None
    agreement_name: Optional[str] = None

    for key, agr in _UK_AGREEMENTS.items():
        if origin in ("GB", "UK") and dest in agr["partner_countries"]:
            agreement_key = key
            agreement_name = agr["name"]
            break
        elif dest in ("GB", "UK") and origin in agr["partner_countries"]:
            agreement_key = key
            agreement_name = agr["name"]
            break

    if agreement_key:
        gates.append(_gate(
            "gate_1_mfn",
            "PREFERENTIAL_AVAILABLE",
            f"Preferential agreement found: {agreement_name}. MFN rates may be avoided.",
        ))
    else:
        gates.append(_gate(
            "gate_1_mfn",
            "MFN_ONLY",
            f"No preferential agreement found for {origin}→{dest}. MFN rates apply.",
        ))
        warnings.append(
            f"No preferential trade agreement covers {origin}→{dest}. "
            "MFN (Most-Favoured-Nation) tariff rates will apply."
        )

    # -----------------------------------------------------------------------
    # Gate 2 – Document completeness
    # -----------------------------------------------------------------------
    required_docs = ["commercial_invoice", "packing_list"]
    if chapter == "72":
        required_docs.append("mill_test_certificate")

    missing_docs = [d for d in required_docs if d not in docs]
    if missing_docs:
        gates.append(_gate(
            "gate_2_documents",
            "INCOMPLETE",
            f"Missing documents: {', '.join(missing_docs)}.",
        ))
        warnings.append(f"Document check: missing {', '.join(missing_docs)}.")
    else:
        gates.append(_gate(
            "gate_2_documents",
            "COMPLETE",
            "All mandatory documents present.",
        ))

    # -----------------------------------------------------------------------
    # Gate 3A – Wholly Obtained
    # -----------------------------------------------------------------------
    origin_status = "UNKNOWN"
    origin_qualified = False

    if wholly_obtained:
        origin_status = "WHOLLY_OBTAINED"
        origin_qualified = True
        gates.append(_gate(
            "gate_3a_wholly_obtained",
            "PASS",
            "Goods declared wholly obtained in origin country. Origin test satisfied.",
        ))
        # Skip remaining origin tests
        return _build_result(
            origin_status=origin_status,
            origin_qualified=origin_qualified,
            agreement_key=agreement_key,
            agreement_name=agreement_name,
            exporter_ref=exporter_ref,
            shipment_value_gbp=shipment_value_gbp,
            origin=origin,
            chapter=chapter,
            gates=gates,
            warnings=warnings,
        )

    gates.append(_gate(
        "gate_3a_wholly_obtained",
        "FAIL",
        "Goods not declared as wholly obtained. Proceeding to PSR/CTH check.",
    ))

    # -----------------------------------------------------------------------
    # Gate 3B – PSR / Change of Tariff Heading (CTH)
    # -----------------------------------------------------------------------
    psr_note = _PSR_NOTES.get(chapter, "")
    if psr_note:
        warnings.append(f"PSR note for Chapter {chapter}: {psr_note}")

    if ctsh_satisfied is True:
        origin_status = "SUFFICIENT_PROCESSING"
        origin_qualified = True
        gates.append(_gate(
            "gate_3b_psr_cth",
            "PASS",
            "Change of Tariff Heading / Sub-Heading (CTH/CTSH) satisfied. "
            f"Input HS codes: {materials_hs_codes or []}. "
            "Product-Specific Rule met.",
        ))
        return _build_result(
            origin_status=origin_status,
            origin_qualified=origin_qualified,
            agreement_key=agreement_key,
            agreement_name=agreement_name,
            exporter_ref=exporter_ref,
            shipment_value_gbp=shipment_value_gbp,
            origin=origin,
            chapter=chapter,
            gates=gates,
            warnings=warnings,
        )
    elif ctsh_satisfied is False:
        gates.append(_gate(
            "gate_3b_psr_cth",
            "FAIL",
            "CTH/CTSH rule not satisfied. Proceeding to cumulation check.",
        ))
    else:
        gates.append(_gate(
            "gate_3b_psr_cth",
            "UNKNOWN",
            "CTH/CTSH not evaluated (ctsh_satisfied not provided). "
            "Provide materials_hs_codes and ctsh_satisfied to enable this gate.",
        ))
        warnings.append(
            "PSR/CTH gate skipped — provide ctsh_satisfied=true/false to evaluate."
        )

    # -----------------------------------------------------------------------
    # Gate 3C – Cumulation
    # -----------------------------------------------------------------------
    if cumulation_countries:
        cum_countries = [c.upper() for c in cumulation_countries]
        agr = _UK_AGREEMENTS.get(agreement_key or "", {})
        partner_set = agr.get("partner_countries", set())
        eligible_cum = [c for c in cum_countries if c in partner_set or c in ("GB", "UK")]
        if eligible_cum:
            gates.append(_gate(
                "gate_3c_cumulation",
                "ELIGIBLE",
                f"Cumulation possible with: {', '.join(eligible_cum)} under {agreement_name}.",
            ))
            warnings.append(
                "Cumulation applies: processing in partner countries may count towards "
                "origin. Ensure supplier declarations are obtained."
            )
        else:
            gates.append(_gate(
                "gate_3c_cumulation",
                "NOT_ELIGIBLE",
                f"Cumulation countries {cum_countries} are not party to {agreement_name}.",
            ))
    else:
        gates.append(_gate(
            "gate_3c_cumulation",
            "SKIPPED",
            "No cumulation countries provided.",
        ))

    # -----------------------------------------------------------------------
    # Gate 3D – Sufficient Processing / RVC
    # -----------------------------------------------------------------------
    agr_cfg = _UK_AGREEMENTS.get(agreement_key or "", {})
    rvc_threshold = agr_cfg.get("default_rvc_threshold", 50.0)

    rvc_pct: Optional[float] = None
    if regional_value_content_pct is not None:
        rvc_pct = regional_value_content_pct
    elif non_originating_value is not None and ex_works_price and ex_works_price > 0:
        rvc_pct = round((1 - non_originating_value / ex_works_price) * 100, 2)

    if rvc_pct is not None:
        if rvc_pct >= rvc_threshold:
            origin_status = "SUFFICIENT_PROCESSING"
            origin_qualified = True
            gates.append(_gate(
                "gate_3d_rvc",
                "PASS",
                f"RVC {rvc_pct:.1f}% ≥ threshold {rvc_threshold}%. Sufficient processing confirmed.",
            ))
        else:
            origin_status = "INSUFFICIENT_PROCESSING"
            origin_qualified = False
            gates.append(_gate(
                "gate_3d_rvc",
                "FAIL",
                f"RVC {rvc_pct:.1f}% < threshold {rvc_threshold}%. Insufficient processing.",
            ))
            warnings.append(
                f"RVC {rvc_pct:.1f}% is below the threshold of {rvc_threshold}%. "
                "Origin cannot be claimed; goods do not qualify for preferential rates."
            )
    else:
        gates.append(_gate(
            "gate_3d_rvc",
            "SKIPPED",
            "RVC could not be computed — provide regional_value_content_pct or "
            "non_originating_value + ex_works_price.",
        ))
        warnings.append(
            "RVC gate skipped — insufficient data. "
            "Provide regional_value_content_pct or (non_originating_value, ex_works_price)."
        )

    # -----------------------------------------------------------------------
    # Gate 3E – Final determination
    # -----------------------------------------------------------------------
    if origin_qualified:
        gates.append(_gate(
            "gate_3e_determination",
            "ORIGIN_CONFIRMED",
            f"Goods qualify for {origin} preferential origin under {agreement_name}.",
        ))
    else:
        gates.append(_gate(
            "gate_3e_determination",
            "ORIGIN_DENIED",
            "Goods do not satisfy any origin test. Preferential treatment not available.",
        ))

    return _build_result(
        origin_status=origin_status,
        origin_qualified=origin_qualified,
        agreement_key=agreement_key,
        agreement_name=agreement_name,
        exporter_ref=exporter_ref,
        shipment_value_gbp=shipment_value_gbp,
        origin=origin,
        chapter=chapter,
        gates=gates,
        warnings=warnings,
    )


def _build_result(
    *,
    origin_status: str,
    origin_qualified: bool,
    agreement_key: Optional[str],
    agreement_name: Optional[str],
    exporter_ref: Optional[str],
    shipment_value_gbp: Optional[float],
    origin: str,
    chapter: str,
    gates: List[Dict[str, str]],
    warnings: List[str],
) -> Dict[str, Any]:
    """Gate 3F – build SoO text and final result."""
    declaration_type: Optional[str] = None
    soo_text: Optional[str] = None

    if origin_qualified and agreement_key:
        agr_cfg = _UK_AGREEMENTS[agreement_key]
        threshold = agr_cfg.get("high_value_threshold_gbp", 6000)
        val = shipment_value_gbp or 0.0
        if val <= threshold:
            declaration_type = agr_cfg["low_value_declaration"]
        else:
            declaration_type = agr_cfg["high_value_declaration"]
            warnings.append(
                f"Shipment value GBP {val:,.2f} exceeds GBP {threshold:,}. "
                "A Registered Exporter (REX) statement is required; ensure the exporter "
                "is registered in the REX system."
            )

        tmpl = agr_cfg.get("soo_text_template", "")
        soo_text = tmpl.format(
            exporter_ref=exporter_ref or "N/A",
            origin_country=origin,
        )
        gates.append({
            "gate": "gate_3f_soo",
            "result": declaration_type,
            "detail": f"Statement-on-Origin generated ({declaration_type}).",
        })
    else:
        declaration_type = "NONE"
        gates.append({
            "gate": "gate_3f_soo",
            "result": "NONE",
            "detail": "No preferential origin — no SoO generated.",
        })

    return {
        "origin_status": origin_status,
        "origin_qualified": origin_qualified,
        "agreement": agreement_name,
        "declaration_type": declaration_type,
        "soo_text": soo_text,
        "gates": gates,
        "warnings": warnings,
    }
