from __future__ import annotations

import asyncio
import os
from contextlib import contextmanager
from datetime import datetime
from fastapi import APIRouter, Depends, File, Path, Query, UploadFile
import httpx
import sqlalchemy as sa
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import ok
from app.infrastructure.database.models import IngestionRun, TariffMeasure, VATRate
from app.infrastructure.database.session import get_session
from app.api.v1.tariff.router import _pick_best_duty


router = APIRouter()

@contextmanager
def _temp_env(key: str, value: str | None):
    old = os.environ.get(key)
    if value is None:
        os.environ.pop(key, None)
    else:
        os.environ[key] = value
    try:
        yield
    finally:
        if old is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = old


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
    source: str = Path(..., description="uk_tariff | uk_tariff_full | eu_taric | eu_taric_full | eu_vat"),
    mode: str = Query("async", description="async | sync"),
    hs_codes: str | None = Query(None, description="Comma-separated HS codes for sync TARIC/UK runs"),
):
    source = source.strip().lower()
    mode = mode.strip().lower()

    if mode == "sync":
        hs_codes_val = hs_codes.strip() if isinstance(hs_codes, str) else ""
        if source == "eu_vat":
            from app.infrastructure.ingestion.eu_vat import ingest as ingest_eu_vat
            return ok({"accepted": True, "mode": "sync", "source": source, "result": await asyncio.wait_for(ingest_eu_vat(), timeout=120)})
        if source in {"eu_taric", "eu_taric_full"}:
            from app.infrastructure.ingestion.taric import ingest_delta as ingest_taric
            if source == "eu_taric_full":
                from app.infrastructure.ingestion.taric import ingest_full as ingest_taric_full
                return ok({"accepted": True, "mode": "sync", "source": source, "result": await asyncio.wait_for(ingest_taric_full(), timeout=900)})
            return ok({"accepted": True, "mode": "sync", "source": source, "result": await asyncio.wait_for(ingest_taric(), timeout=300)})
        if source in {"uk_tariff", "uk_tariff_full"}:
            from app.infrastructure.ingestion.ukgt import ingest_delta as ingest_ukgt
            if source == "uk_tariff_full":
                from app.infrastructure.ingestion.ukgt import ingest_full as ingest_ukgt_full
                return ok({"accepted": True, "mode": "sync", "source": source, "result": await asyncio.wait_for(ingest_ukgt_full(), timeout=3600)})
            with _temp_env("UK_TARIFF_HS_CODES", hs_codes_val or None):
                return ok({"accepted": True, "mode": "sync", "source": source, "result": await asyncio.wait_for(ingest_ukgt(), timeout=240)})
        return ok({"accepted": False, "error": "Unknown source"})

    from app.infrastructure.workers.celery_app import celery_app
    if source == "uk_tariff":
        task = "app.infrastructure.workers.tasks.ingest_ukgt_delta"
    elif source == "uk_tariff_full":
        task = "app.infrastructure.workers.tasks.ingest_ukgt_full"
    elif source == "eu_taric":
        task = "app.infrastructure.workers.tasks.ingest_taric_delta"
    elif source == "eu_taric_full":
        task = "app.infrastructure.workers.tasks.ingest_taric_full"
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


@router.post("/taric/xlsx/inspect")
async def taric_xlsx_inspect(
    file: UploadFile = File(...),
    max_rows: int = Query(5, ge=1, le=20),
):
    data = await file.read()
    from app.infrastructure.ingestion.taric_xlsx import inspect_xlsx

    return ok(await inspect_xlsx(data, max_rows=max_rows))


@router.post("/taric/xlsx/import")
async def taric_xlsx_import(
    kind: str = Query(..., description="duties_import | nomenclature_en"),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_session),
):
    kind = kind.strip().lower()
    data = await file.read()

    run = IngestionRun(source="TARIC", status="running", started_at=datetime.utcnow())
    db.add(run)
    await db.commit()
    await db.refresh(run)

    try:
        if kind == "duties_import":
            from app.infrastructure.ingestion.taric_xlsx import ingest_duties_import_xlsx

            result = await ingest_duties_import_xlsx(db, data)
        elif kind == "nomenclature_en":
            from app.infrastructure.ingestion.taric_xlsx import ingest_nomenclature_en_xlsx

            result = await ingest_nomenclature_en_xlsx(db, data)
        else:
            return ok({"accepted": False, "error": "Unknown kind"})

        run.status = "success"
        run.records_processed = int(result.get("measures_upserted") or result.get("hs_codes_upserted") or 0)
        run.completed_at = datetime.utcnow()
        await db.commit()
        return ok({"accepted": True, "kind": kind, "result": result})
    except Exception as exc:
        await db.rollback()
        run.status = "failed"
        run.error_details = str(exc)
        run.completed_at = datetime.utcnow()
        await db.commit()
        return ok({"accepted": False, "kind": kind, "error": str(exc)})


async def _download_bytes(url: str, *, max_bytes: int) -> bytes:
    backoff_s = 0.75
    last_exc: Exception | None = None
    for _ in range(3):
        try:
            async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
                async with client.stream("GET", url, headers={"Accept": "*/*"}) as resp:
                    resp.raise_for_status()
                    buf = bytearray()
                    async for chunk in resp.aiter_bytes():
                        buf.extend(chunk)
                        if len(buf) > max_bytes:
                            raise ValueError("Remote file too large")
                    return bytes(buf)
        except Exception as exc:
            last_exc = exc
            await asyncio.sleep(backoff_s)
            backoff_s *= 2
    raise last_exc or RuntimeError("Download failed")


@router.post("/taric/xlsx/import-from-url")
async def taric_xlsx_import_from_url(
    kind: str = Query(..., description="duties_import | nomenclature_en"),
    url: str = Query(...),
    mode: str = Query("async", description="async | sync"),
    db: AsyncSession = Depends(get_session),
):
    if not (url.startswith("https://") or url.startswith("http://")):
        return ok({"accepted": False, "error": "url must start with http(s)://"})

    kind = kind.strip().lower()
    mode = mode.strip().lower()

    if mode == "async":
        from app.infrastructure.workers.celery_app import celery_app

        r = celery_app.send_task(
            "app.infrastructure.workers.tasks.ingest_taric_xlsx_from_url",
            args=[kind, url],
            kwargs={},
            queue="data_ingestion",
        )
        return ok({"accepted": True, "mode": "async", "kind": kind, "url": url, "task_id": str(r.id)})
    run = IngestionRun(source="TARIC", status="running", started_at=datetime.utcnow())
    db.add(run)
    await db.commit()
    await db.refresh(run)


    try:
        data = await _download_bytes(url, max_bytes=80 * 1024 * 1024)
        if kind == "duties_import":
            from app.infrastructure.ingestion.taric_xlsx import ingest_duties_import_xlsx

            result = await ingest_duties_import_xlsx(db, data)
        elif kind == "nomenclature_en":
            from app.infrastructure.ingestion.taric_xlsx import ingest_nomenclature_en_xlsx

            result = await ingest_nomenclature_en_xlsx(db, data)
        else:
            return ok({"accepted": False, "error": "Unknown kind"})

        run.status = "success"
        run.records_processed = int(result.get("measures_upserted") or result.get("hs_codes_upserted") or 0)
        run.completed_at = datetime.utcnow()
        await db.commit()
        return ok({"accepted": True, "kind": kind, "url": url, "result": result})
    except Exception as exc:
        await db.rollback()
        run.status = "failed"
        run.error_details = str(exc)
        run.completed_at = datetime.utcnow()
        await db.commit()
        return ok({"accepted": False, "kind": kind, "url": url, "error": str(exc)})


@router.get("/sample/complete")
async def sample_complete_lookups(
    destination_country: str = Query("DE"),
    origin_country: str = Query("CN"),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_session),
):
    dest = destination_country.upper()
    origin = origin_country.upper()
    market = "EU" if dest not in {"GB", "UK"} else "GB"

    hs_res = await db.execute(
        select(TariffMeasure.hs_code)
        .where(TariffMeasure.jurisdiction == market)
        .order_by(sa.func.random())
        .limit(limit * 5)
    )
    hs_codes = [r[0] for r in hs_res.all() if isinstance(r[0], str)]

    vat_res = await db.execute(
        select(VATRate)
        .where(VATRate.jurisdiction == market, VATRate.country_code == dest)
        .order_by(VATRate.ingested_at.desc())
        .limit(1)
    )
    vat = vat_res.scalar_one_or_none()

    out: list[dict] = []
    for hs in hs_codes:
        duty = await _pick_best_duty(db, hs_code=hs, market=market, origin=origin)
        if not duty:
            continue
        out.append(
            {
                "hs_code": hs,
                "destination_market": market,
                "destination_country": dest,
                "origin_country": origin,
                "duty": {
                    "rate_type": duty.measure_type,
                    "duty_rate": float(duty.rate_ad_valorem) if duty.rate_ad_valorem is not None else None,
                    "duty_amount": float(duty.rate_specific_amount) if duty.rate_specific_amount is not None else None,
                    "rate_specific_unit": duty.rate_specific_unit,
                    "source": duty.source_dataset,
                },
                "vat": {
                    "country_code": vat.country_code if vat else dest,
                    "rate_type": vat.rate_type if vat else None,
                    "vat_rate": float(vat.vat_rate) if vat else None,
                    "source": vat.source if vat else None,
                },
            }
        )
        if len(out) >= limit:
            break

    return ok({"count": len(out), "items": out})
