"""
Tariff Service.

Wraps the tariff adapter and translates TariffData into the response-level
MeasuresResult and ComplianceResult shapes.
"""
from __future__ import annotations

import logging
from typing import Any

from app.adapters.tariff_adapter import get_tariff_data
from app.schemas.import_analysis import ComplianceResult, MeasuresResult, TariffData

logger = logging.getLogger(__name__)


async def fetch(
    hs_code: str,
    origin: str,
    destination: str,
) -> TariffData:
    """Retrieve raw tariff data for the given trade lane."""
    return await get_tariff_data(
        hs_code=hs_code,
        origin=origin,
        destination=destination,
    )


def to_measures(data: TariffData) -> MeasuresResult:
    """Convert TariffData → MeasuresResult for the API response."""
    other: list[dict[str, Any]] = list(data.other_measures)

    if data.anti_dumping:
        other.append({
            "type": "anti_dumping",
            "rate_pct": data.anti_dumping_rate,
            "description": "Anti-dumping duty applicable for this origin",
        })
    if data.countervailing:
        other.append({
            "type": "countervailing",
            "rate_pct": data.countervailing_rate,
            "description": "Countervailing / subsidy duty applicable for this origin",
        })

    return MeasuresResult(
        anti_dumping=data.anti_dumping,
        anti_dumping_rate=data.anti_dumping_rate,
        countervailing=data.countervailing,
        countervailing_rate=data.countervailing_rate,
        excise=data.excise,
        excise_rate=data.excise_rate,
        other_measures=other,
    )


def to_compliance(data: TariffData) -> ComplianceResult:
    """Convert TariffData → ComplianceResult for the API response."""
    return ComplianceResult(
        documents_required=data.documents_required,
        notes=data.tariff_notes,
    )
