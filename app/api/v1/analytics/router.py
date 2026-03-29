from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from uuid import UUID

from fastapi import APIRouter, Depends
import sqlalchemy as sa
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, get_current_user
from app.core.responses import ok
from app.infrastructure.database.models import CalculationProfile, HSCode, IngestionRun, TariffMeasure, VATRate
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
    symbol = {"GBP": "£", "EUR": "€", "USD": "$"}.get(currency.upper(), "")
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
async def analytics_kpis(
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    uid = UUID(user.id)
    now = datetime.now(timezone.utc)
    start_cur = _start_of_month(now)
    start_prev = _start_of_prev_month(now)

    base = select(CalculationProfile).where(CalculationProfile.user_id == uid)

    # ── Total profiles (= total analyses) ────────────────────────────────────
    total_calcs: int = (
        await db.execute(select(func.count(CalculationProfile.id)).where(CalculationProfile.user_id == uid))
    ).scalar_one()

    # ── Total landed cost summed from last_result JSONB ───────────────────────
    # last_result -> calculation -> total_landed_cost (float)
    # last_result -> calculation -> currency (str)
    # We sum per currency and return the dominant one (most profiles).
    total_amount: Decimal | None = None
    total_currency: str = "EUR"
    try:
        landed_expr = sa.cast(
            CalculationProfile.last_result["calculation"]["total_landed_cost"].astext,
            sa.Numeric(24, 6),
        )
        currency_expr = CalculationProfile.last_result["calculation"]["currency"].astext

        # Find which currency has the most profiles with a value
        currency_row = (
            await db.execute(
                select(currency_expr, func.count())
                .where(
                    CalculationProfile.user_id == uid,
                    CalculationProfile.last_result["calculation"]["total_landed_cost"].astext != None,
                )
                .group_by(currency_expr)
                .order_by(func.count().desc())
                .limit(1)
            )
        ).first()
        if currency_row:
            total_currency = currency_row[0] or "EUR"

        raw = (
            await db.execute(
                select(func.coalesce(func.sum(landed_expr), 0)).where(
                    CalculationProfile.user_id == uid,
                    currency_expr == total_currency,
                )
            )
        ).scalar_one()
        total_amount = Decimal(str(raw)) if raw is not None else None
    except Exception:
        total_amount = None

    # ── Avg confidence from last_result JSONB ────────────────────────────────
    # last_result -> classification -> confidence (0.0–1.0)
    avg_conf_pct: float | None = None
    try:
        conf_expr = sa.cast(
            CalculationProfile.last_result["classification"]["confidence"].astext,
            sa.Numeric(5, 4),
        )
        avg_conf = (
            await db.execute(
                select(func.avg(conf_expr)).where(CalculationProfile.user_id == uid)
            )
        ).scalar_one()
        avg_conf_pct = float(avg_conf * 100) if avg_conf is not None else None
    except Exception:
        avg_conf_pct = None

    # ── This month / last month counts ───────────────────────────────────────
    this_month_calcs: int = (
        await db.execute(
            select(func.count(CalculationProfile.id)).where(
                CalculationProfile.user_id == uid,
                CalculationProfile.created_at >= start_cur,
            )
        )
    ).scalar_one()

    last_month_calcs: int = (
        await db.execute(
            select(func.count(CalculationProfile.id)).where(
                CalculationProfile.user_id == uid,
                CalculationProfile.created_at >= start_prev,
                CalculationProfile.created_at < start_cur,
            )
        )
    ).scalar_one()

    delta_vs_last_month = int(this_month_calcs) - int(last_month_calcs)

    # ── Tariff data counts (global, not user-scoped) ──────────────────────────
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
            "dashboard": {
                "total_calculated": {
                    "amount": str(total_amount) if total_amount is not None else None,
                    "currency": total_currency,
                    "display": _compact_money(total_amount, total_currency) if total_amount is not None else None,
                    "calcs": int(total_calcs),
                },
                "avg_confidence": {
                    "pct": round(avg_conf_pct, 1) if avg_conf_pct is not None else None,
                    "calcs": int(total_calcs),
                },
                "this_month": {
                    "calcs": int(this_month_calcs),
                    "delta_vs_last_month": int(delta_vs_last_month),
                },
            },
        }
    )
