from __future__ import annotations

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import ok
from app.infrastructure.database.models import IngestionRun
from app.infrastructure.database.session import get_session


router = APIRouter()


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

    r = celery_app.send_task(task, kwargs={}, queue="data_ingestion")
    return ok({"accepted": True, "source": source, "task_id": str(r.id)})


@router.post("/trigger/eu_vat")
async def trigger_eu_vat():
    from app.infrastructure.workers.celery_app import celery_app

    r = celery_app.send_task("app.infrastructure.workers.tasks.ingest_eu_vat", kwargs={}, queue="data_ingestion")
    return ok({"accepted": True, "source": "eu_vat", "task_id": str(r.id)})


@router.post("/trigger/uk_tariff")
async def trigger_uk_tariff():
    from app.infrastructure.workers.celery_app import celery_app

    r = celery_app.send_task("app.infrastructure.workers.tasks.ingest_ukgt_delta", kwargs={}, queue="data_ingestion")
    return ok({"accepted": True, "source": "uk_tariff", "task_id": str(r.id)})


@router.post("/trigger/eu_taric")
async def trigger_eu_taric():
    from app.infrastructure.workers.celery_app import celery_app

    r = celery_app.send_task("app.infrastructure.workers.tasks.ingest_taric_delta", kwargs={}, queue="data_ingestion")
    return ok({"accepted": True, "source": "eu_taric", "task_id": str(r.id)})


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


@router.get("/celery/ping")
async def celery_ping():
    from app.infrastructure.workers.celery_app import celery_app

    try:
        replies = celery_app.control.ping(timeout=1.5)
        return ok({"replies": replies})
    except Exception as exc:
        return ok({"replies": [], "error": str(exc)})


@router.get("/celery/task/{task_id}")
async def celery_task_status(task_id: str = Path(...)):
    from app.infrastructure.workers.celery_app import celery_app

    result = celery_app.AsyncResult(task_id)
    payload: dict = {"task_id": task_id, "state": result.state, "ready": result.ready()}
    if result.ready():
        try:
            payload["result"] = result.get(timeout=0.1)
        except Exception as exc:
            payload["result_error"] = str(exc)
    else:
        info = result.info
        if info is not None:
            payload["info"] = str(info)
    return ok(payload)
