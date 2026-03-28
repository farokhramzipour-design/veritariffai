from celery import shared_task


@shared_task(name="app.infrastructure.workers.tasks.ingest_taric_delta", queue="data_ingestion")
def ingest_taric_delta():
    from app.infrastructure.database.session import run_migrations_sync
    from app.infrastructure.ingestion.taric import ingest_delta_sync

    run_migrations_sync(raise_on_error=True)
    return ingest_delta_sync()


@shared_task(name="app.infrastructure.workers.tasks.ingest_taric_full", queue="data_ingestion")
def ingest_taric_full():
    from app.infrastructure.database.session import run_migrations_sync
    from app.infrastructure.ingestion.taric import ingest_full_sync

    run_migrations_sync(raise_on_error=True)
    return ingest_full_sync()


@shared_task(name="app.infrastructure.workers.tasks.ingest_ukgt_delta", queue="data_ingestion")
def ingest_ukgt_delta():
    from app.infrastructure.database.session import run_migrations_sync
    from app.infrastructure.ingestion.ukgt import ingest_delta_sync

    run_migrations_sync(raise_on_error=True)
    return ingest_delta_sync()


@shared_task(name="app.infrastructure.workers.tasks.ingest_ukgt_full", queue="data_ingestion")
def ingest_ukgt_full():
    from app.infrastructure.database.session import run_migrations_sync
    from app.infrastructure.ingestion.ukgt import ingest_full_sync

    run_migrations_sync(raise_on_error=True)
    return ingest_full_sync()


@shared_task(name="app.infrastructure.workers.tasks.ingest_eu_vat", queue="data_ingestion")
def ingest_eu_vat():
    from app.infrastructure.database.session import run_migrations_sync
    from app.infrastructure.ingestion.eu_vat import ingest_sync

    run_migrations_sync(raise_on_error=True)
    return ingest_sync()


@shared_task(name="app.infrastructure.workers.tasks.ingest_taric_xlsx_from_url", queue="data_ingestion")
def ingest_taric_xlsx_from_url(kind: str, url: str):
    import asyncio
    from datetime import datetime

    import httpx

    from app.infrastructure.database.models import IngestionRun
    from app.infrastructure.database.session import AsyncSessionMaker, run_migrations_sync
    from app.infrastructure.ingestion.taric_xlsx import ingest_duties_import_xlsx, ingest_nomenclature_en_xlsx

    run_migrations_sync(raise_on_error=True)

    async def _download_bytes(remote_url: str, *, max_bytes: int) -> bytes:
        backoff_s = 0.75
        last_exc: Exception | None = None
        for _ in range(3):
            try:
                async with httpx.AsyncClient(timeout=180, follow_redirects=True) as client:
                    async with client.stream("GET", remote_url, headers={"Accept": "*/*"}) as resp:
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

    async def _run():
        async with AsyncSessionMaker() as db:
            run = IngestionRun(source="TARIC", status="running", started_at=datetime.utcnow())
            db.add(run)
            await db.commit()
            await db.refresh(run)

            try:
                data = await _download_bytes(url, max_bytes=80 * 1024 * 1024)
                k = (kind or "").strip().lower()
                if k == "duties_import":
                    result = await ingest_duties_import_xlsx(db, data)
                elif k == "nomenclature_en":
                    result = await ingest_nomenclature_en_xlsx(db, data)
                else:
                    raise ValueError("Unknown kind")

                run.status = "success"
                run.records_processed = int(result.get("measures_upserted") or result.get("hs_codes_upserted") or 0)
                run.completed_at = datetime.utcnow()
                await db.commit()
                return {"accepted": True, "kind": k, "result": result}
            except Exception as exc:
                await db.rollback()
                run.status = "failed"
                run.error_details = str(exc)
                run.completed_at = datetime.utcnow()
                await db.commit()
                return {"accepted": False, "kind": kind, "error": str(exc)}

    return asyncio.run(_run())


@shared_task(name="app.infrastructure.workers.tasks.ingest_fx_hmrc", queue="data_ingestion")
def ingest_fx_hmrc():
    from app.infrastructure.database.session import run_migrations_sync
    from app.infrastructure.ingestion.fx import ingest_hmrc_monthly

    run_migrations_sync(raise_on_error=True)
    return ingest_hmrc_monthly()


@shared_task(name="app.infrastructure.workers.tasks.ingest_fx_ecb", queue="data_ingestion")
def ingest_fx_ecb():
    from app.infrastructure.database.session import run_migrations_sync
    from app.infrastructure.ingestion.fx import ingest_ecb_daily

    run_migrations_sync(raise_on_error=True)
    return ingest_ecb_daily()
