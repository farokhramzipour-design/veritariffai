"""
Origin Rules Service.

Evaluates whether a shipment qualifies for preferential duty treatment based
on bilateral / regional trade agreements between the origin and destination.

Design principle: no AI involved here — preferential eligibility is a legal
determination based on treaty rules, not a probabilistic classification.

Swap-in path: replace the lookup tables with a call to:
  - EU TARIC preference measures (measure type 142)
  - HMRC Tariff Preference lookup
  - Your compiled trade agreement rules database
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from app.schemas.import_analysis import OriginRulesResult
from app.utils import country as country_util

logger = logging.getLogger(__name__)


@dataclass
class _Agreement:
    """Describes a bilateral or regional trade agreement."""

    name: str
    preferential_rate: Optional[float]          # None = rate depends on HS heading
    proof_of_origin: str                         # Required proof document
    notes: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Agreement registry: (origin_bloc_or_country, destination_bloc_or_country)
#
# Convention:
#   "EU"  = any EU-27 member state
#   "UK"  = GB or UK
#   ISO-2 = specific country
#
# Rates marked as None require per-HS lookup (not implemented in mock).
# ---------------------------------------------------------------------------

def _evaluate(origin: str, destination: str) -> Optional[_Agreement]:
    """Return the most favourable applicable agreement, or None."""
    o = origin.upper()
    d = destination.upper()

    o_is_eu = country_util.is_eu(o)
    d_is_eu = country_util.is_eu(d)
    d_is_uk = d in ("GB", "UK")

    # ── EU internal trade: no customs duty between member states ──────────
    if o_is_eu and d_is_eu:
        return _Agreement(
            name="EU Single Market (internal trade)",
            preferential_rate=0.0,
            proof_of_origin="Not required (free movement of goods)",
            notes=["No customs duty applies between EU member states."],
        )

    # ── UK → EU TCA ──────────────────────────────────────────────────────
    if o in ("GB", "UK") and d_is_eu:
        return _Agreement(
            name="UK-EU Trade and Cooperation Agreement (TCA)",
            preferential_rate=0.0,
            proof_of_origin="Statement on Origin (TCA Annex ORIG-4) or REX",
            notes=[
                "0% preference applies for goods with UK preferential origin.",
                "Product-specific rules (PSR) must be met.",
                "Statement on origin required on the invoice for values > EUR 6,000.",
            ],
        )

    # ── EU → UK TCA ──────────────────────────────────────────────────────
    if o_is_eu and d_is_uk:
        return _Agreement(
            name="UK-EU Trade and Cooperation Agreement (TCA)",
            preferential_rate=0.0,
            proof_of_origin="Statement on Origin or EUR.1",
            notes=[
                "0% preference applies for goods with EU preferential origin.",
                "PSR compliance required.",
            ],
        )

    # ── EU GSP (for imports INTO EU from qualifying LDC/developing countries) ──
    if d_is_eu:
        if country_util.eu_gsp_eligible(o):
            return _Agreement(
                name="EU Generalised Scheme of Preferences (GSP)",
                preferential_rate=None,  # depends on HS heading
                proof_of_origin="Form A or REX (Registered Exporter) statement",
                notes=[
                    "Preferential rate varies by HS heading — verify in TARIC.",
                    "China was graduated out of EU GSP in 2015 for most goods.",
                ],
            )
        if country_util.eu_gsp_plus_eligible(o):
            return _Agreement(
                name="EU GSP+ (Enhanced Framework)",
                preferential_rate=0.0,
                proof_of_origin="REX Registered Exporter statement",
                notes=["Enhanced 0% preference — verify in TARIC by HS code."],
            )

    # ── Switzerland ↔ EU ──────────────────────────────────────────────────
    if o == "CH" and d_is_eu:
        return _Agreement(
            name="EU-Switzerland Bilateral Agreements (1972 Free Trade Agreement)",
            preferential_rate=0.0,
            proof_of_origin="EUR.1 Movement Certificate or invoice declaration",
            notes=["Covers industrial goods. Agricultural goods treated separately."],
        )
    if o_is_eu and d == "CH":
        return _Agreement(
            name="EU-Switzerland Bilateral Agreements",
            preferential_rate=0.0,
            proof_of_origin="EUR.1 or invoice declaration",
        )

    # ── Norway / EEA ─────────────────────────────────────────────────────
    if o in ("NO", "IS", "LI") and d_is_eu:
        return _Agreement(
            name="EEA Agreement",
            preferential_rate=0.0,
            proof_of_origin="EUR.1 or invoice declaration",
        )

    # ── Japan ↔ EU ────────────────────────────────────────────────────────
    if o == "JP" and d_is_eu:
        return _Agreement(
            name="EU-Japan Economic Partnership Agreement (EPA)",
            preferential_rate=None,
            proof_of_origin="Origin declaration by approved exporter or REX",
            notes=["Phased tariff elimination — rate depends on HS code and tariff elimination schedule."],
        )

    # ── South Korea ↔ EU ─────────────────────────────────────────────────
    if o == "KR" and d_is_eu:
        return _Agreement(
            name="EU-Korea Free Trade Agreement",
            preferential_rate=0.0,
            proof_of_origin="EUR.1 or approved exporter origin declaration",
        )

    # ── Canada ↔ EU CETA ─────────────────────────────────────────────────
    if o == "CA" and d_is_eu:
        return _Agreement(
            name="EU-Canada Comprehensive Economic and Trade Agreement (CETA)",
            preferential_rate=0.0,
            proof_of_origin="Origin declaration by approved exporter",
        )

    # ── Vietnam ↔ EU EVFTA ───────────────────────────────────────────────
    if o == "VN" and d_is_eu:
        return _Agreement(
            name="EU-Vietnam Free Trade Agreement (EVFTA)",
            preferential_rate=None,
            proof_of_origin="EUR.1 or REX statement",
            notes=["Staged tariff elimination — verify rate by HS code."],
        )

    # No preferential agreement found
    return None


async def evaluate(
    origin: str,
    destination: str,
    hs_code: str,
    duty_rate: Optional[float],
) -> OriginRulesResult:
    """
    Determine whether the origin → destination trade lane qualifies for
    preferential duty treatment.

    Args:
        origin:       ISO-2 country of origin.
        destination:  ISO-2 importing country.
        hs_code:      HS code (used for PSR notes; rate lookup is agreement-level only).
        duty_rate:    MFN duty rate (used to check if preference adds value).
    """
    agreement = _evaluate(origin, destination)

    if agreement is None:
        logger.info(
            "origin_rules: no preferential agreement for %s → %s",
            origin, destination,
        )
        return OriginRulesResult(
            preferential_eligible=False,
            preferential_duty_rate=None,
            agreement_name=None,
            proof_of_origin_required=None,
            notes=["No preferential trade agreement found for this origin-destination pair."],
        )

    # If preferential rate is None, it means per-HS lookup is needed
    pref_rate = agreement.preferential_rate

    logger.info(
        "origin_rules: agreement='%s' pref_rate=%s origin=%s dest=%s",
        agreement.name,
        pref_rate,
        origin,
        destination,
    )

    return OriginRulesResult(
        preferential_eligible=True,
        preferential_duty_rate=pref_rate,
        agreement_name=agreement.name,
        proof_of_origin_required=agreement.proof_of_origin,
        notes=agreement.notes + (
            [f"Verify the exact preferential rate for HS {hs_code} in the agreement schedule."]
            if pref_rate is None else []
        ),
    )
