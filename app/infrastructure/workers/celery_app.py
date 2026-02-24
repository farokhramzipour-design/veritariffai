from celery import Celery
from celery.schedules import crontab
from app.config import settings


celery_app = Celery(
    "tce",
    broker=(settings.celery_broker_url or settings.redis_url),
    backend=(settings.celery_backend_url or settings.redis_url),
)

celery_app.conf.update(
    task_queues=None,
    task_default_queue="default",
    beat_schedule={
        "ingest_taric_delta": {
            "task": "app.infrastructure.workers.tasks.ingest_taric_delta",
            "schedule": crontab(minute=0, hour=6),
            "options": {"queue": "data_ingestion"},
        },
        "ingest_ukgt_delta": {
            "task": "app.infrastructure.workers.tasks.ingest_ukgt_delta",
            "schedule": crontab(minute=30, hour=6),
            "options": {"queue": "data_ingestion"},
        },
        "ingest_taric_full": {
            "task": "app.infrastructure.workers.tasks.ingest_taric_full",
            "schedule": crontab(minute=0, hour=2, day_of_week="sun"),
            "options": {"queue": "data_ingestion"},
        },
        "ingest_ukgt_full": {
            "task": "app.infrastructure.workers.tasks.ingest_ukgt_full",
            "schedule": crontab(minute=0, hour=3, day_of_week="sun"),
            "options": {"queue": "data_ingestion"},
        },
        "ingest_fx_hmrc": {
            "task": "app.infrastructure.workers.tasks.ingest_fx_hmrc",
            "schedule": crontab(minute=0, hour=9, day_of_month="1"),
            "options": {"queue": "data_ingestion"},
        },
        "ingest_fx_ecb": {
            "task": "app.infrastructure.workers.tasks.ingest_fx_ecb",
            "schedule": crontab(minute=0, hour=16),
            "options": {"queue": "data_ingestion"},
        },
    },
)
