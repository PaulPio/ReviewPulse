"""Job status polling and ingestion triggers."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_author
from app.db.base import get_db
from app.models.author import Author
from app.models.book import Book
from app.models.ingestion_job import IngestionJob
from app.schemas.job import JobOut

router = APIRouter()


@router.get("/{job_id}", response_model=JobOut)
async def get_job(
    job_id: uuid.UUID,
    current_author: Author = Depends(get_current_author),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(IngestionJob).where(
            IngestionJob.id == job_id,
            IngestionJob.author_id == current_author.id,
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobOut.model_validate(job)


@router.get("", response_model=list[JobOut])
async def list_jobs(
    current_author: Author = Depends(get_current_author),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(IngestionJob)
        .where(IngestionJob.author_id == current_author.id)
        .order_by(IngestionJob.created_at.desc())
        .limit(50)
    )
    return [JobOut.model_validate(j) for j in result.scalars().all()]


@router.post("/books/{book_id}/ingest", response_model=JobOut, status_code=status.HTTP_202_ACCEPTED)
async def trigger_ingestion(
    book_id: uuid.UUID,
    current_author: Author = Depends(get_current_author),
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger an ingestion job for a book.

    POST /api/v1/books/{book_id}/ingest

    Returns 202 Accepted immediately with the job record.
    Poll GET /api/v1/jobs/{job_id} for status updates.
    Returns 409 if a job is already queued/running for this book.
    """
    # Verify book belongs to author (tenant isolation)
    book_result = await db.execute(
        select(Book).where(Book.id == book_id, Book.author_id == current_author.id)
    )
    if not book_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Book not found")

    # Prevent pile-up
    existing = await db.execute(
        select(IngestionJob).where(
            IngestionJob.book_id == book_id,
            IngestionJob.status.in_(["queued", "running"]),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="A job is already running for this book")

    job = IngestionJob(
        id=uuid.uuid4(),
        book_id=book_id,
        author_id=current_author.id,
        status="queued",
    )
    db.add(job)
    await db.flush()

    # Dispatch to Celery — fire and forget, returns 202 immediately
    from app.tasks.ingestion import run_ingestion_job
    celery_task = run_ingestion_job.delay(str(job.id))
    job.celery_task_id = celery_task.id
    await db.flush()

    return JobOut.model_validate(job)
