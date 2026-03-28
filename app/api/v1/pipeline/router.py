from __future__ import annotations

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_admin_key
from app.core.responses import ok
from app.infrastructure.database.models import IngestionRun
from app.infrastructure.database.session import get_session


router = APIRouter(dependencies=[Depends(require_admin_key)])


@router.get("/status")
async def pipeline_status(db: AsyncSession = Depends(get_session)):
    sources = ["TARIC", "UK_TARIFF", "EU_VAT"]
    out: dict[str, dict] = {}
    for source in sources:
        res = await db.execute(
            select(IngestionRun)
            .where(IngestionRun.source == source)
            .order_by(IngestionRun.started_at.desc())
            .limit(1)
        )
        run = res.scalar_one_or_none()
        out[source] = {
            "status": run.status if run else None,
            "records_processed": run.records_processed if run else None,
            "started_at": run.started_at.isoformat() if run and run.started_at else None,
            "completed_at": run.completed_at.isoformat() if run and run.completed_at else None,
            "error_details": run.error_details if run else None,
        }
    return ok(out)


@router.post("/trigger/{source}")
async def trigger_pipeline(
    source: str = Path(..., description="uk_tariff | eu_taric | eu_vat"),
):
    from app.infrastructure.workers.celery_app import celery_app

    source = source.strip().lower()
    if source == "uk_tariff":
        task = "app.infrastructure.workers.tasks.ingest_ukgt_delta"
    elif source == "eu_taric":
        task = "app.infrastructure.workers.tasks.ingest_taric_delta"
    elif source == "eu_vat":
        task = "app.infrastructure.workers.tasks.ingest_eu_vat"
    else:
        return ok({"accepted": False, "error": "Unknown source"})

    r = celery_app.send_task(task, kwargs={})
    return ok({"accepted": True, "source": source, "task_id": str(r.id)})


@router.get("/logs")
async def pipeline_logs(
    source: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_session),
):
    stmt = select(IngestionRun).order_by(IngestionRun.started_at.desc()).limit(limit)
    if source:
        stmt = stmt.where(IngestionRun.source == source)
    res = await db.execute(stmt)
    runs = res.scalars().all()
    return ok([
        {
            "id": str(r.id),
            "source": r.source,
            "status": r.status,
            "records_processed": r.records_processed,
            "records_inserted": r.records_inserted,
            "records_updated": r.records_updated,
            "error_details": r.error_details,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        }
        for r in runs
    ])

