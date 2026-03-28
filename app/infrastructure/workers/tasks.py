from celery import shared_task


@shared_task(name="app.infrastructure.workers.tasks.ingest_taric_delta", queue="data_ingestion")
def ingest_taric_delta():
    from app.infrastructure.ingestion.taric import ingest_delta_sync

    return ingest_delta_sync()


@shared_task(name="app.infrastructure.workers.tasks.ingest_taric_full", queue="data_ingestion")
def ingest_taric_full():
    from app.infrastructure.ingestion.taric import ingest_full_sync

    return ingest_full_sync()


@shared_task(name="app.infrastructure.workers.tasks.ingest_ukgt_delta", queue="data_ingestion")
def ingest_ukgt_delta():
    from app.infrastructure.ingestion.ukgt import ingest_delta_sync

    return ingest_delta_sync()


@shared_task(name="app.infrastructure.workers.tasks.ingest_ukgt_full", queue="data_ingestion")
def ingest_ukgt_full():
    from app.infrastructure.ingestion.ukgt import ingest_full_sync

    return ingest_full_sync()


@shared_task(name="app.infrastructure.workers.tasks.ingest_eu_vat", queue="data_ingestion")
def ingest_eu_vat():
    from app.infrastructure.ingestion.eu_vat import ingest_sync

    return ingest_sync()


@shared_task(name="app.infrastructure.workers.tasks.ingest_fx_hmrc", queue="data_ingestion")
def ingest_fx_hmrc():
    from app.infrastructure.ingestion.fx import ingest_hmrc_monthly

    return ingest_hmrc_monthly()


@shared_task(name="app.infrastructure.workers.tasks.ingest_fx_ecb", queue="data_ingestion")
def ingest_fx_ecb():
    from app.infrastructure.ingestion.fx import ingest_ecb_daily

    return ingest_ecb_daily()
