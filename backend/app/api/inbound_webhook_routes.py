"""N10: signed inbound webhook to trigger ingestion without browser session."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.schemas import IngestionWebhookAck, IngestionWebhookIn
from app.dependencies import get_db_session
from app.models import Book, Job, JobKind, JobStatus
from app.services.webhook import effective_ingestion_secret, verify_request_signature
from app.tasks import run_ingest_job

router = APIRouter(tags=["webhooks"])


@router.post("/webhooks/ingestion", response_model=IngestionWebhookAck)
async def ingestion_webhook(
    request: Request,
    db: Session = Depends(get_db_session),
) -> IngestionWebhookAck:
    secret = effective_ingestion_secret()
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhook ingestion secret not configured (WEBHOOK_INGESTION_SECRET or WEBHOOK_SIGNING_SECRET)",
        )
    body = await request.body()
    hdr = request.headers.get("X-ReviewPulse-Signature")
    verify_request_signature(hdr, body, secret)
    try:
        payload = IngestionWebhookIn.model_validate_json(body)
    except (json.JSONDecodeError, ValidationError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid body: {e}") from e

    book = db.get(Book, payload.book_id)
    if book is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="book not found")

    author_id = book.author_id
    key = (payload.idempotency_key or "").strip() or None
    if key:
        existing = db.scalar(
            select(Job).where(
                Job.author_id == author_id,
                Job.book_id == book.id,
                Job.kind == JobKind.ingest_book,
                Job.idempotency_key == key,
            )
        )
        if existing is not None:
            return IngestionWebhookAck(job_id=existing.id, deduped=True)

    job = Job(
        author_id=author_id,
        book_id=book.id,
        kind=JobKind.ingest_book,
        status=JobStatus.queued,
        job_data={"source": "inbound_webhook"},
        idempotency_key=key,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    run_ingest_job.delay(str(job.id))
    return IngestionWebhookAck(job_id=job.id, deduped=False)
