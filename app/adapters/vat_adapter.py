"""
VAT / import tax adapter.

Provides import VAT rates by destination country.  These rates are official
statutory rates — the AI classifier is NEVER consulted for VAT figures.

Swap-in path: replace `get_vat_data()` body with a call to:
  - EU Commission VIES / TEDB database
  - HMRC VAT rates API
  - Your compiled VAT rates database
"""
from __future__ import annotations

import logging

from app.schemas.import_analysis import VATData
from app.utils import hs as hs_util

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Standard import VAT rates by ISO-2 destination country.
# Sources: European Commission VAT rates database (2025).
# ---------------------------------------------------------------------------

_STANDARD_VAT_RATES: dict[str, float] = {
    # EU-27
    "AT": 20.0, "BE": 21.0, "BG": 20.0, "HR": 25.0, "CY": 19.0,
    "CZ": 21.0, "DK": 25.0, "EE": 22.0, "FI": 25.5, "FR": 20.0,
    "DE": 19.0, "GR": 24.0, "HU": 27.0, "IE": 23.0, "IT": 22.0,
    "LV": 21.0, "LT": 21.0, "LU": 17.0, "MT": 18.0, "NL": 21.0,
    "PL": 23.0, "PT": 23.0, "RO": 19.0, "SK": 20.0, "SI": 22.0,
    "ES": 21.0, "SE": 25.0,
    # Non-EU
    "GB": 20.0, "UK": 20.0,   # UK VAT (post-Brexit)
    "NO": 25.0,                # Norwegian MVA
    "CH": 8.1,                 # Swiss MWST / TVA (2024 rate)
    "US": 0.0,                 # No federal sales/import VAT in the US
    "JP": 10.0,                # Japanese consumption tax
    "AU": 10.0,                # Australian GST
    "CA": 5.0,                 # Federal GST (provincial taxes extra)
    "SG": 9.0,                 # Singapore GST
    "CN": 13.0,                # Chinese VAT on imports
    "IN": 18.0,                # India GST (standard rate)
    "BR": 18.0,                # ICMS approximate rate
    "KR": 10.0,
    "TR": 20.0,
    "AE": 5.0,                 # UAE VAT
    "SA": 15.0,                # Saudi Arabia VAT
}

# ---------------------------------------------------------------------------
# Reduced-rate HS chapters for EU destinations (simplified)
# Real implementation requires heading/subheading-level rules from TEDB.
# ---------------------------------------------------------------------------

_EU_REDUCED_CHAPTERS: frozenset[str] = frozenset({
    "04",  # Dairy (some reduced in certain member states)
    "09",  # Coffee/tea
    "10",  # Cereals
    "22",  # Water / non-alcoholic beverages (some member states)
    "49",  # Books / newspapers (zero/reduced in many EU states)
    "30",  # Pharmaceuticals
})

_EU_ZERO_CHAPTERS: frozenset[str] = frozenset({
    "27",  # Natural gas / kerosene (zero-rated in some member states)
})


async def get_vat_data(
    destination: str,
    hs_code: str,
) -> VATData:
    """
    Retrieve the import VAT rate applicable in *destination* for *hs_code*.

    Returns a VATData object.  If the destination is unknown, VAT rate will be
    None and a note will indicate manual verification is required.
    """
    dest = destination.upper()
    chap = hs_util.chapter(hs_code)

    standard_rate = _STANDARD_VAT_RATES.get(dest)
    notes: list[str] = []

    if standard_rate is None:
        notes.append(
            f"No VAT rate data available for destination '{dest}'. "
            "Verify the applicable import tax at the national tax authority."
        )
        logger.warning("vat_adapter: no VAT rate for destination=%s", dest)
        return VATData(vat_rate=None, vat_category="UNKNOWN", vat_notes=notes)

    # Apply simplified chapter-level reduced/zero rate logic for EU
    from app.utils.country import is_eu
    if is_eu(dest):
        if chap in _EU_ZERO_CHAPTERS:
            notes.append(f"Zero-rate may apply in some EU member states for HS chapter {chap}.")
            vat_category = "REDUCED"
        elif chap in _EU_REDUCED_CHAPTERS:
            notes.append(
                f"A reduced VAT rate may apply in {dest} for HS chapter {chap} — "
                "verify with the national tax authority."
            )
            vat_category = "REDUCED"
        else:
            vat_category = "STANDARD"
    else:
        vat_category = "STANDARD"

    logger.info(
        "vat_adapter: dest=%s hs=%s vat=%.1f%% category=%s",
        dest, hs_code, standard_rate, vat_category,
    )

    return VATData(
        vat_rate=standard_rate,
        vat_category=vat_category,
        vat_notes=notes,
    )
