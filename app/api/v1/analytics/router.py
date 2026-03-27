from __future__ import annotations
from datetime import datetime, timezone, timedelta
from calendar import monthrange
from uuid import UUID
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, cast, Numeric
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, get_current_user
from app.core.responses import ok
from app.infrastructure.database.models import CalculationResult
from app.infrastructure.database.session import get_session


router = APIRouter()


def _uid(user: CurrentUser) -> UUID:
    return UUID(user.id)


def _month_bounds(dt: datetime) -> tuple[datetime, datetime]:
    year, month = dt.year, dt.month
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    last_day = monthrange(year, month)[1]
    end = datetime(year, month, last_day, 23, 59, 59, tzinfo=timezone.utc)
    return start, end


@router.get(
    "/kpis",
    summary="Key analytics KPIs for the current user",
)
async def kpis(
    currency: str = Query("GBP", min_length=3, max_length=3, description="Display currency label"),
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    uid = _uid(user)

    # JSONB paths for total amount – support both {totals.total.amount} and {totals.total_landed_cost.amount}
    total_amount_expr_primary = cast(CalculationResult.totals["total"]["amount"].astext, Numeric(18, 2))
    total_amount_expr_alt = cast(CalculationResult.totals["total_landed_cost"]["amount"].astext, Numeric(18, 2))
    total_amount_expr = func.coalesce(total_amount_expr_primary, total_amount_expr_alt)

    # Overall aggregates
    agg_query = select(
        func.count(CalculationResult.id),
        func.coalesce(func.sum(total_amount_expr), Decimal("0.00")),
        func.coalesce(func.avg(CalculationResult.confidence_score), 0.0),
    ).where(CalculationResult.user_id == uid)
    agg_res = await db.execute(agg_query)
    total_count, total_amount, avg_conf = agg_res.one()

    # This month vs last month
    now = datetime.now(timezone.utc)
    this_start, this_end = _month_bounds(now)
    last_month = (now.replace(day=1) - timedelta(days=1))
    last_start, last_end = _month_bounds(last_month)

    this_q = select(func.count(CalculationResult.id)).where(
        CalculationResult.user_id == uid,
        CalculationResult.created_at >= this_start,
        CalculationResult.created_at <= this_end,
    )
    last_q = select(func.count(CalculationResult.id)).where(
        CalculationResult.user_id == uid,
        CalculationResult.created_at >= last_start,
        CalculationResult.created_at <= last_end,
    )
    this_count = (await db.execute(this_q)).scalar_one()
    last_count = (await db.execute(last_q)).scalar_one()
    delta = int(this_count) - int(last_count or 0)

    return ok({
        "total_calculated": {
            "amount": f"{Decimal(total_amount or 0):.2f}",
            "currency": currency.upper(),
            "calc_count": int(total_count or 0),
        },
        "avg_confidence_pct": round(float(avg_conf or 0) * 100, 1),
        "this_month": {
            "count": int(this_count or 0),
            "delta_vs_last_month": delta,
        },
    })
