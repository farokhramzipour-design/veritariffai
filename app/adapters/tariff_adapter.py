"""
Tariff data adapter.

This module is the ONLY place that provides official duty rates and trade measures.
The AI classifier is expressly forbidden from producing these values.

Current implementation: structured mock dataset.
Swap-in path: replace `get_tariff_data()` body with a call to
  - EU TARIC API  (https://ec.europa.eu/taxation_customs/dds2/taric)
  - HMRC Trade Tariff API  (https://api.trade-tariff.service.gov.uk)
  - WCO data (licensed)
  - Your own compiled tariff database

The function signature, return type, and error behaviour MUST remain stable
when the real adapter is wired in.
"""
from __future__ import annotations

import logging
from typing import Any

from app.schemas.import_analysis import TariffData
from app.utils import country as country_util
from app.utils import hs as hs_util

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# EU MFN ad-valorem duty rates by HS chapter (simplified).
# Source: EU Common Customs Tariff (CCT) — indicative rates only.
# In production these come from TARIC or a licensed tariff database.
# ---------------------------------------------------------------------------

_EU_MFN_BY_CHAPTER: dict[str, float] = {
    "01": 0.0,   "02": 12.8, "03": 9.6,  "04": 17.3, "05": 0.0,
    "06": 0.0,   "07": 11.5, "08": 9.0,  "09": 0.0,  "10": 0.0,
    "11": 9.7,   "12": 0.0,  "13": 0.0,  "14": 0.0,  "15": 5.1,
    "16": 16.6,  "17": 19.2, "18": 9.6,  "19": 9.7,  "20": 14.4,
    "21": 4.5,   "22": 7.2,  "23": 0.0,  "24": 74.9, "25": 0.0,
    "26": 0.0,   "27": 2.0,  "28": 3.2,  "29": 3.7,  "30": 0.0,
    "31": 3.2,   "32": 3.2,  "33": 3.7,  "34": 2.7,  "35": 4.2,
    "36": 0.0,   "37": 3.7,  "38": 5.0,  "39": 4.7,  "40": 3.2,
    "41": 3.0,   "42": 3.7,  "43": 3.7,  "44": 2.0,  "45": 3.0,
    "46": 3.7,   "47": 0.0,  "48": 2.0,  "49": 0.0,  "50": 3.7,
    "51": 5.0,   "52": 8.0,  "53": 3.7,  "54": 8.0,  "55": 8.0,
    "56": 5.0,   "57": 5.0,  "58": 8.0,  "59": 5.0,  "60": 8.0,
    "61": 12.0,  "62": 12.0, "63": 6.5,  "64": 8.0,  "65": 3.7,
    "66": 4.7,   "67": 4.7,  "68": 3.0,  "69": 5.5,  "70": 5.0,
    "71": 2.5,   "72": 3.0,  "73": 3.7,  "74": 3.0,  "75": 3.0,
    "76": 4.0,   "77": 0.0,  "78": 3.5,  "79": 3.5,  "80": 3.5,
    "81": 3.7,   "82": 3.7,  "83": 2.7,  "84": 1.7,  "85": 2.7,
    "86": 3.0,   "87": 6.5,  "88": 0.0,  "89": 2.7,  "90": 2.0,
    "91": 3.7,   "92": 3.5,  "93": 2.5,  "94": 3.7,  "95": 2.7,
    "96": 3.5,   "97": 0.0,
}

# ---------------------------------------------------------------------------
# Anti-dumping / countervailing measures for CN → EU (selected examples).
# In production: query TARIC measure type 551/552/672 filtered by origin geo.
# ---------------------------------------------------------------------------

# Keyed by (chapter_prefix, origin_country)
_ANTI_DUMPING: dict[tuple[str, str], dict[str, Any]] = {
    # Steel flat-rolled products from China
    ("72", "CN"): {
        "anti_dumping": True,
        "anti_dumping_rate": 47.8,
        "note": "EU anti-dumping on steel products from CN — verify current rate in TARIC",
    },
    # Solar glass (Chapter 70) from China
    ("70", "CN"): {
        "anti_dumping": True,
        "anti_dumping_rate": 17.1,
        "note": "EU anti-dumping on solar glass from CN",
    },
    # Aluminium from China (Chapter 76)
    ("76", "CN"): {
        "anti_dumping": True,
        "anti_dumping_rate": 30.2,
        "note": "EU anti-dumping on aluminium products from CN",
    },
    # Electric vehicles from China (Chapter 87, BEV)
    ("87", "CN"): {
        "anti_dumping": False,
        "countervailing": True,
        "countervailing_rate": 35.3,
        "note": "EU countervailing duty on BEV from CN — applies to HS 8703.10 / 8703.80",
    },
}

# ---------------------------------------------------------------------------
# Document requirements by HS chapter (simplified)
# ---------------------------------------------------------------------------

_DOCS_BY_CHAPTER: dict[str, list[str]] = {
    "02": ["Veterinary / sanitary certificate", "Health certificate from exporting country"],
    "03": ["Health certificate", "Catch certificate (if wild-caught seafood)"],
    "04": ["Veterinary certificate", "Health mark"],
    "10": ["Phytosanitary certificate"],
    "29": ["Material Safety Data Sheet (MSDS / SDS)"],
    "38": ["Material Safety Data Sheet (MSDS / SDS)", "REACH compliance declaration"],
    "62": ["Country of origin declaration or certificate"],
    "72": ["Mill Test Certificate (EN 10204)", "Country of origin certificate"],
    "87": ["Certificate of Conformity (CoC)", "Type-approval documentation"],
    "88": ["EASA / airworthiness certification"],
    "93": ["Export licence from origin country", "End-user certificate"],
}


def _mfn_rate(hs_code: str, destination: str) -> float | None:
    """Look up the MFN duty rate for a destination tariff bloc."""
    if country_util.is_eu(destination):
        chap = hs_util.chapter(hs_code)
        return _EU_MFN_BY_CHAPTER.get(chap)
    # GB / UK (simplified)
    if destination in ("GB", "UK"):
        chap = hs_util.chapter(hs_code)
        # UK Global Tariff broadly mirrors EU CCT with some differences
        return _EU_MFN_BY_CHAPTER.get(chap)
    # Default: unknown tariff schedule → return None (indicate no data)
    return None


def _measures(hs_code: str, origin: str, destination: str) -> dict[str, Any]:
    """Return any anti-dumping / countervailing measures applicable."""
    chap = hs_util.chapter(hs_code)
    # Measures are currently indexed by (chapter, origin) for EU imports
    if country_util.is_eu(destination):
        key = (chap, origin.upper())
        return _ANTI_DUMPING.get(key, {})
    return {}


def _documents(hs_code: str) -> list[str]:
    chap = hs_util.chapter(hs_code)
    return _DOCS_BY_CHAPTER.get(chap, [])


async def get_tariff_data(
    hs_code: str,
    origin: str,
    destination: str,
) -> TariffData:
    """
    Retrieve duty rates and trade measures for the given trade route.

    Args:
        hs_code:     6-digit (or more) HS code.
        origin:      ISO-2 country of origin.
        destination: ISO-2 importing country.

    Returns:
        TariffData populated from the mock dataset (or a real API in production).
    """
    origin = origin.upper()
    destination = destination.upper()

    duty_rate = _mfn_rate(hs_code, destination)
    measures = _measures(hs_code, origin, destination)
    docs = _documents(hs_code)

    notes: list[str] = []
    if duty_rate is None:
        notes.append(
            f"No tariff data available for destination '{destination}'. "
            "Rate shown is indicative only — verify at the official tariff portal."
        )
        duty_rate = 0.0  # Safe fallback

    if measures.get("note"):
        notes.append(measures["note"])

    logger.info(
        "tariff_adapter: hs=%s origin=%s dest=%s duty=%.1f%% AD=%s",
        hs_code, origin, destination,
        duty_rate,
        measures.get("anti_dumping", False),
    )

    return TariffData(
        duty_rate=duty_rate,
        anti_dumping=measures.get("anti_dumping", False),
        anti_dumping_rate=measures.get("anti_dumping_rate"),
        countervailing=measures.get("countervailing", False),
        countervailing_rate=measures.get("countervailing_rate"),
        excise=False,
        excise_rate=None,
        other_measures=[],
        documents_required=docs,
        tariff_notes=notes,
    )
