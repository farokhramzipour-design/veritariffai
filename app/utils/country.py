"""
Country code utilities.

Normalises ISO 3166-1 alpha-2 codes and maps them to common customs-relevant
metadata (tariff bloc membership, VAT applicability, etc.).
"""
from __future__ import annotations

# EU-27 member states (ISO alpha-2)
EU27: frozenset[str] = frozenset({
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR",
    "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL",
    "PL", "PT", "RO", "SK", "SI", "ES", "SE",
})

# EEA (EU + Iceland, Liechtenstein, Norway)
EEA: frozenset[str] = EU27 | frozenset({"IS", "LI", "NO"})

# Countries with GSP access to EU (simplified — production: load from DB)
EU_GSP_COUNTRIES: frozenset[str] = frozenset({
    "BD", "PK", "KH", "MM", "ET", "MZ", "TZ", "UG", "KE",
    # China was graduated out of EU GSP for most goods in 2015
})

# Countries under EU GSP+ (enhanced)
EU_GSP_PLUS_COUNTRIES: frozenset[str] = frozenset({
    "AM", "AZ", "BO", "CV", "KG", "MN", "PK", "PH", "LK",
})

# Countries with a UK trade agreement post-Brexit
UK_FTA_COUNTRIES: frozenset[str] = frozenset({
    "AU", "NZ", "JP", "SG", "CA", "MX", "CL", "CO", "PE",
    "VN", "KR", "TN", "MA", "EG", "GH", "KE",
    # UK-EU TCA covered separately as GB↔EU bloc
})


def normalise(code: str) -> str:
    """Strip whitespace and uppercase an ISO-2 code."""
    return code.strip().upper()


def is_eu(code: str) -> bool:
    return normalise(code) in EU27


def is_eea(code: str) -> bool:
    return normalise(code) in EEA


def eu_gsp_eligible(origin: str) -> bool:
    """True if *origin* benefits from EU GSP for imports INTO the EU."""
    return normalise(origin) in EU_GSP_COUNTRIES


def eu_gsp_plus_eligible(origin: str) -> bool:
    return normalise(origin) in EU_GSP_PLUS_COUNTRIES


def uk_fta_eligible(origin: str) -> bool:
    """True if *origin* has a UK FTA (for imports INTO GB)."""
    return normalise(origin) in UK_FTA_COUNTRIES
