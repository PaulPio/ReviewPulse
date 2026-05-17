from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "reviewpulse",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks"],
)

celery_app.conf.timezone = "UTC"
celery_app.conf.task_track_started = True
celery_app.conf.beat_schedule = {
    "reingest-catalog-hourly": {
        "task": "app.tasks.scheduled_refresh_all",
        "schedule": crontab(minute=0),
    },
}
