from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import ok
from app.infrastructure.database.models import HSCode, IngestionRun, TariffMeasure, VATRate
from app.infrastructure.database.session import get_session


router = APIRouter()


@router.get("/kpis")
async def analytics_kpis(db: AsyncSession = Depends(get_session)):
    hs_count = (await db.execute(select(func.count()).select_from(HSCode))).scalar_one()
    measures_count = (await db.execute(select(func.count()).select_from(TariffMeasure))).scalar_one()
    vat_count = (await db.execute(select(func.count()).select_from(VATRate))).scalar_one()

    latest_runs: dict[str, dict] = {}
    for source in ("TARIC", "UK_TARIFF_FULL", "UK_TARIFF", "EU_VAT"):
        res = await db.execute(
            select(IngestionRun)
            .where(IngestionRun.source == source)
            .order_by(IngestionRun.started_at.desc())
            .limit(1)
        )
        r = res.scalar_one_or_none()
        latest_runs[source] = {
            "status": r.status if r else None,
            "records_processed": r.records_processed if r else None,
            "started_at": r.started_at.isoformat() if r and r.started_at else None,
            "completed_at": r.completed_at.isoformat() if r and r.completed_at else None,
        }

    return ok(
        {
            "tariff": {
                "hs_codes": int(hs_count),
                "measures": int(measures_count),
                "vat_rates": int(vat_count),
            },
            "pipeline": {"latest_runs": latest_runs},
        }
    )

