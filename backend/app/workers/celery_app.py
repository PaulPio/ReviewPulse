"""
Celery application factory.

Beat schedule (F9)
------------------
`refresh_all_books` runs every `settings.refresh_interval_seconds` (default 1h).
It enqueues an ingestion job for every book in the system.

Trade-off note (ARCHITECTURE.md)
---------------------------------
Celery Beat on a single worker is simple but not HA. In production with
multiple workers, use `django-celery-beat` (DB-backed schedule) or a
separate Beat container to avoid double-firing. For this project,
single-worker Beat is acceptable.
"""

from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "reviewpulse",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.tasks.ingestion",
        "app.tasks.webhook",
        "app.tasks.scheduled",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,          # Re-queue on worker crash
    worker_prefetch_multiplier=1, # Fair dispatch — important for long analysis tasks
    result_expires=86400,         # Results kept 24h in Redis
    beat_schedule={
        "refresh-all-books-hourly": {
            "task": "app.tasks.scheduled.refresh_all_books",
            "schedule": settings.refresh_interval_seconds,
        },
    },
)
