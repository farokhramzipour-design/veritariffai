from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends
import sqlalchemy as sa
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import ok
from app.infrastructure.database.models import CalculationResult, HSCode, IngestionRun, TariffMeasure, VATRate
from app.infrastructure.database.session import get_session


router = APIRouter()


def _start_of_month(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _start_of_prev_month(dt: datetime) -> datetime:
    cur = _start_of_month(dt)
    year = cur.year
    month = cur.month - 1
    if month == 0:
        month = 12
        year -= 1
    return cur.replace(year=year, month=month)


def _compact_money(amount: Decimal | None, currency: str) -> str | None:
    if amount is None:
        return None
    symbol = "£" if currency.upper() == "GBP" else ""
    a = abs(amount)
    sign = "-" if amount < 0 else ""
    if a >= Decimal("1000000000"):
        return f"{sign}{symbol}{(a / Decimal('1000000000')).quantize(Decimal('0.1'))}B"
    if a >= Decimal("1000000"):
        return f"{sign}{symbol}{(a / Decimal('1000000')).quantize(Decimal('0.1'))}M"
    if a >= Decimal("1000"):
        return f"{sign}{symbol}{(a / Decimal('1000')).quantize(Decimal('0.1'))}K"
    return f"{sign}{symbol}{a.quantize(Decimal('0.01'))}"


@router.get("/kpis")
async def analytics_kpis(db: AsyncSession = Depends(get_session)):
    hs_count = (await db.execute(select(func.count()).select_from(HSCode))).scalar_one()
    measures_count = (await db.execute(select(func.count()).select_from(TariffMeasure))).scalar_one()
    vat_count = (await db.execute(select(func.count()).select_from(VATRate))).scalar_one()

    total_calcs = (await db.execute(select(func.count()).select_from(CalculationResult))).scalar_one()
    avg_conf = (await db.execute(select(func.avg(CalculationResult.confidence_score)))).scalar_one()
    avg_conf_pct = float(avg_conf * 100) if avg_conf is not None else None

    now = datetime.now(timezone.utc)
    start_cur = _start_of_month(now)
    start_prev = _start_of_prev_month(now)

    this_month_calcs = (
        await db.execute(select(func.count()).select_from(CalculationResult).where(CalculationResult.created_at >= start_cur))
    ).scalar_one()
    last_month_calcs = (
        await db.execute(
            select(func.count())
            .select_from(CalculationResult)
            .where(CalculationResult.created_at >= start_prev, CalculationResult.created_at < start_cur)
        )
    ).scalar_one()
    delta_vs_last_month = int(this_month_calcs) - int(last_month_calcs)

    total_currency = "GBP"
    total_amount: Decimal | None = None
    try:
        amount_expr = sa.cast(
            CalculationResult.totals["total_landed_cost"]["amount"].astext, sa.Numeric(24, 6)
        )
        currency_expr = CalculationResult.totals["total_landed_cost"]["currency"].astext
        total_amount = (
            await db.execute(select(func.coalesce(func.sum(amount_expr), 0)).where(currency_expr == total_currency))
        ).scalar_one()
    except Exception:
        total_amount = None

    try:
        if total_amount is not None and not isinstance(total_amount, Decimal):
            total_amount = Decimal(str(total_amount))
    except (InvalidOperation, TypeError):
        total_amount = None

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
            "dashboard": {
                "total_calculated": {
                    "amount": str(total_amount) if total_amount is not None else None,
                    "currency": total_currency,
                    "display": _compact_money(total_amount, total_currency) if total_amount is not None else None,
                    "calcs": int(total_calcs),
                },
                "avg_confidence": {
                    "pct": avg_conf_pct,
                    "calcs": int(total_calcs),
                },
                "this_month": {
                    "calcs": int(this_month_calcs),
                    "delta_vs_last_month": int(delta_vs_last_month),
                },
            },
        }
    )
