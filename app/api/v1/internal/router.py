from fastapi import APIRouter
from app.core.responses import ok


router = APIRouter()


@router.post("/ingestion/taric/trigger")
async def trigger_taric_ingestion():
    from app.infrastructure.workers.celery_app import celery_app

    r1 = celery_app.send_task("app.infrastructure.workers.tasks.ingest_taric_delta", kwargs={})
    return ok({"task_id": str(r1.id)})


@router.post("/ingestion/ukgt/trigger")
async def trigger_ukgt_ingestion():
    from app.infrastructure.workers.celery_app import celery_app

    r1 = celery_app.send_task("app.infrastructure.workers.tasks.ingest_ukgt_delta", kwargs={})
    return ok({"task_id": str(r1.id)})


@router.post("/ingestion/fx/trigger")
async def trigger_fx_ingestion():
    from app.infrastructure.workers.celery_app import celery_app

    r1 = celery_app.send_task("app.infrastructure.workers.tasks.ingest_fx_hmrc", kwargs={})
    r2 = celery_app.send_task("app.infrastructure.workers.tasks.ingest_fx_ecb", kwargs={})
    return ok({"task_ids": [str(r1.id), str(r2.id)]})


@router.get("/ingestion/status")
async def ingestion_status():
    return ok({"runs": []})


@router.post("/cache/invalidate")
async def cache_invalidate():
    return ok({"invalidated": True})


@router.get("/data-quality/report")
async def data_quality_report():
    return ok({"valid": True, "metrics": {}})

