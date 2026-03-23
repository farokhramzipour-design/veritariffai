"""
Harmonized System (HS) code utilities.

Validation, normalisation, and chapter/heading extraction helpers.
"""
from __future__ import annotations

import re


def strip(code: str) -> str:
    """Remove dots, spaces, and non-digit characters."""
    return re.sub(r"[^0-9]", "", code)


def is_valid(code: str) -> bool:
    """True if code is 4–10 digits after stripping."""
    digits = strip(code)
    return 4 <= len(digits) <= 10


def chapter(code: str) -> str:
    """Return the 2-digit chapter (e.g. '62' for '620342')."""
    return strip(code)[:2]


def heading(code: str) -> str:
    """Return the 4-digit heading (e.g. '6203')."""
    return strip(code)[:4]


def subheading_6(code: str) -> str:
    """Return the 6-digit international subheading."""
    d = strip(code)
    return d[:6] if len(d) >= 6 else d.ljust(6, "0")


def normalise(code: str, target_digits: int = 6) -> str:
    """
    Normalise an HS code to *target_digits* precision.

    Pads with zeros if shorter; truncates if longer.
    """
    d = strip(code)
    return d[:target_digits].ljust(target_digits, "0")


def format_display(code: str) -> str:
    """
    Format an HS code for human display with dots.

    Examples:
        '620342' → '6203.42'
        '6203420000' → '6203.42.00.00'
    """
    d = strip(code)
    if len(d) <= 4:
        return d
    if len(d) <= 6:
        return f"{d[:4]}.{d[4:]}"
    if len(d) <= 8:
        return f"{d[:4]}.{d[4:6]}.{d[6:]}"
    return f"{d[:4]}.{d[4:6]}.{d[6:8]}.{d[8:]}"
