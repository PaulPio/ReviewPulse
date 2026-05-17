"""Job status polling endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_author
from app.db.base import get_db
from app.models.author import Author
from app.models.ingestion_job import IngestionJob
from app.schemas.job import JobOut

router = APIRouter()

_TERMINAL = frozenset({"completed", "failed", "partial"})


@router.get("/{job_id}", response_model=JobOut)
async def get_job(
    job_id: uuid.UUID,
    response: Response,
    current_author: Author = Depends(get_current_author),
    db: AsyncSession = Depends(get_db),
):
    """
    Poll the status of an ingestion job.

    Async polling contract
    ----------------------
    This endpoint is the *pull* side of a fire-and-forget async pattern:

    1. POST /api/v1/books/{id}/ingest  →  202 Accepted, job.status="queued"
    2. Client polls GET /api/v1/jobs/{id} on a back-off interval.
    3. Stop when status is one of: completed | failed | partial

    "async, not just await" — the trigger does not block the HTTP connection;
    it enqueues a Celery task and returns immediately.  The caller polls
    independently; there is no open connection or push callback.  This
    follows RFC 9110 §15.3.3 (202 Accepted for long-running operations).

    Cache-Control
    -------------
    Active states (queued / running): no-store — always fetch fresh.
    Terminal states (completed / failed / partial): max-age=300 — safe to
    cache because the status will never change again.
    """
    result = await db.execute(
        select(IngestionJob).where(
            IngestionJob.id == job_id,
            IngestionJob.author_id == current_author.id,
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status in _TERMINAL:
        response.headers["Cache-Control"] = "max-age=300"
    else:
        response.headers["Cache-Control"] = "no-store"

    return JobOut.model_validate(job)


@router.get("", response_model=list[JobOut])
async def list_jobs(
    current_author: Author = Depends(get_current_author),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=100),
):
    """List the most-recent ingestion jobs for the authenticated author."""
    result = await db.execute(
        select(IngestionJob)
        .where(IngestionJob.author_id == current_author.id)
        .order_by(IngestionJob.created_at.desc())
        .limit(limit)
    )
    return [JobOut.model_validate(j) for j in result.scalars().all()]
