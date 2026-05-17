"""
Scheduled Celery Beat tasks (F9).

`refresh_all_books` fires every `settings.refresh_interval_seconds` (default 1h).
It enqueues a new IngestionJob for every book that hasn't had a successful
ingestion in the last hour, avoiding re-queuing books already in progress.

Idempotency
-----------
We only create a new job if the book's most recent job is NOT in
{queued, running} state. This prevents pile-up if the worker is slow.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.logging import get_logger
from app.db.base import AsyncSessionLocal
from app.models.book import Book
from app.models.ingestion_job import IngestionJob
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="app.tasks.scheduled.refresh_all_books")
def refresh_all_books() -> dict:
    return asyncio.run(_refresh())


async def _refresh() -> dict:
    from app.tasks.ingestion import run_ingestion_job

    async with AsyncSessionLocal() as db:
        books_q = select(Book)
        books_result = await db.execute(books_q)
        books: list[Book] = list(books_result.scalars().all())

        enqueued = 0
        skipped = 0

        for book in books:
            # Check for an active job
            active_q = select(IngestionJob).where(
                IngestionJob.book_id == book.id,
                IngestionJob.status.in_(["queued", "running"]),
            )
            active_result = await db.execute(active_q)
            if active_result.scalars().first():
                skipped += 1
                continue

            # Create a new job
            job = IngestionJob(
                book_id=book.id,
                author_id=book.author_id,
                status="queued",
            )
            db.add(job)
            await db.flush()

            run_ingestion_job.delay(str(job.id))
            enqueued += 1

        await db.commit()

    logger.info(
        "scheduled.refresh_complete",
        total_books=len(books),
        enqueued=enqueued,
        skipped=skipped,
    )
    return {"enqueued": enqueued, "skipped": skipped}
