from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.schemas import JobOut
from app.dependencies import current_author, get_db_session
from app.models import Author, Job

router = APIRouter(tags=["jobs"])


@router.get("/jobs/{job_id}", response_model=JobOut)
def get_job(
    job_id: uuid.UUID,
    author: Author = Depends(current_author),
    db: Session = Depends(get_db_session),
) -> Job:
    job = db.get(Job, job_id)
    if job is None or job.author_id != author.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


@router.get("/jobs", response_model=list[JobOut])
def list_jobs(
    author: Author = Depends(current_author),
    db: Session = Depends(get_db_session),
    limit: int = 20,
) -> list[Job]:
    from sqlalchemy import select

    rows = db.scalars(
        select(Job)
        .where(Job.author_id == author.id)
        .order_by(Job.created_at.desc())
        .limit(min(limit, 100))
    ).all()
    return list(rows)
