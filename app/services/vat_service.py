"""
VAT Service — wraps the VAT adapter.
"""
from __future__ import annotations

import logging

from app.adapters.vat_adapter import get_vat_data
from app.schemas.import_analysis import VATData

logger = logging.getLogger(__name__)


async def fetch(destination: str, hs_code: str) -> VATData:
    """Retrieve VAT data for the import destination and HS code."""
    return await get_vat_data(destination=destination, hs_code=hs_code)
