from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.celery_app import celery_app
from app.config import get_settings
from app.db import SessionLocal
from app.llm.mock import MockLLMClient
from app.llm.openrouter import OpenRouterClient
from app.llm.protocol import LLMClient
from app.logging_config import get_logger
from app.models import Book, Job, JobKind, JobStatus, Review, ReviewAnalysis
from app.services.webhook import deliver_ingestion_webhook

log = get_logger("tasks")


def get_worker_llm() -> LLMClient:
    if os.environ.get("USE_MOCK_LLM") == "1":
        return MockLLMClient()
    return OpenRouterClient()


def sample_catalog_path() -> Path:
    settings = get_settings()
    if settings.sample_reviews_path:
        return Path(settings.sample_reviews_path)
    return Path(__file__).resolve().parent / "data" / "sample_reviews.json"


def load_samples_by_asin() -> dict[str, list[dict]]:
    path = sample_catalog_path()
    raw = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, list[dict]] = {}
    for item in raw.get("items", []):
        out[str(item["asin"]).upper()] = list(item.get("reviews", []))
    return out


def upsert_reviews(db: Session, book: Book, rows: list[dict]) -> list[UUID]:
    created_or_touched: list[UUID] = []
    for row in rows:
        ext = row["external_key"]
        existing = db.scalar(
            select(Review).where(Review.book_id == book.id, Review.external_key == ext)
        )
        review_date = row.get("review_date")
        rd: datetime | None = None
        if review_date:
            rd = datetime.fromisoformat(str(review_date).replace("Z", "+00:00"))
        if existing:
            existing.body = row.get("body", existing.body)
            existing.rating = row.get("rating", existing.rating)
            existing.review_date = rd or existing.review_date
            db.add(existing)
            created_or_touched.append(existing.id)
        else:
            r = Review(
                book_id=book.id,
                external_key=ext,
                body=row["body"],
                rating=row.get("rating"),
                review_date=rd,
            )
            db.add(r)
            db.flush()
            created_or_touched.append(r.id)
    db.commit()
    return created_or_touched


def analyze_if_needed(db: Session, review_id: UUID, llm: LLMClient) -> None:
    review = db.get(Review, review_id)
    if review is None:
        return
    if review.analysis is not None:
        return
    log.info("analyze_start", review_id=str(review_id))
    try:
        analysis, usage = llm.analyze_review(review.body, review.rating)
        db.add(
            ReviewAnalysis(
                review_id=review.id,
                sentiment=analysis.sentiment,
                sentiment_confidence=analysis.sentiment_confidence,
                themes=analysis.themes,
                ai_generated=analysis.ai_generated,
                ai_generated_confidence=analysis.ai_generated_confidence,
                summary=analysis.summary,
                actionable=analysis.actionable,
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                estimated_cost_usd=usage.estimated_cost_usd,
                model_id=usage.model_id,
            )
        )
        db.commit()
    except Exception as e:
        log.error("analyze_failed", review_id=str(review_id), error=str(e), exc_info=True)
        db.rollback()
        raise

    review = db.get(Review, review_id)
    assert review is not None
    if review.embedding is not None:
        return
    log.info("embed_start", review_id=str(review_id))
    try:
        vectors, u2 = llm.embed_texts([review.body])
        review.embedding = vectors[0]
        if review.analysis:
            review.analysis.prompt_tokens += u2.prompt_tokens
            review.analysis.estimated_cost_usd += u2.estimated_cost_usd
        db.add(review)
        db.commit()
    except Exception as e:
        log.error(
            "embed_failed",
            review_id=str(review_id),
            error=str(e),
            exc_info=True,
        )
        db.rollback()
        raise


def _fail_job(db: Session, job: Job, msg: str) -> None:
    job.status = JobStatus.failed
    job.error_message = msg
    db.add(job)
    db.commit()


@celery_app.task(name="app.tasks.run_ingest_job")
def run_ingest_job(job_id: str) -> None:
    jid = UUID(job_id)
    llm = get_worker_llm()
    db = SessionLocal()
    job = db.get(Job, jid)
    if job is None:
        log.error("job_missing", job_id=job_id)
        db.close()
        return
    job.status = JobStatus.running
    db.add(job)
    db.commit()
    book = db.get(Book, job.book_id) if job.book_id else None
    if book is None:
        _fail_job(db, job, "Book not found")
        db.close()
        return
    samples = load_samples_by_asin()
    asin = (book.asin or "").upper()
    rows = samples.get(asin, [])
    if not rows:
        log.warning("no_sample_reviews_for_asin", asin=asin, book_id=str(book.id))
        job.status = JobStatus.completed
        job.job_data = {**job.job_data, "ingested": 0, "note": "no_fixture_rows_for_asin"}
        db.add(job)
        db.commit()
        deliver_ingestion_webhook(
            {"job_id": str(job.id), "status": job.status.value, "book_id": str(book.id)}
        )
        db.close()
        return
    try:
        ids = upsert_reviews(db, book, rows)
        partial = False
        for rid in ids:
            try:
                analyze_if_needed(db, rid, llm)
            except Exception:
                partial = True
        job.status = JobStatus.partial if partial else JobStatus.completed
        job.job_data = {
            **job.job_data,
            "ingested": len(rows),
            "review_ids": [str(i) for i in ids],
        }
        db.add(job)
        db.commit()
        deliver_ingestion_webhook(
            {"job_id": str(job.id), "status": job.status.value, "book_id": str(book.id)}
        )
    except Exception as e:
        log.error("ingest_failed", job_id=job_id, error=str(e), exc_info=True)
        _fail_job(db, job, str(e))
        deliver_ingestion_webhook(
            {"job_id": str(job.id), "status": JobStatus.failed.value, "error": str(e)}
        )
    finally:
        db.close()


@celery_app.task(name="app.tasks.scheduled_refresh_all")
def scheduled_refresh_all() -> None:
    """Queue re-ingestion for all books (idempotent ingest)."""
    db = SessionLocal()
    try:
        books = db.scalars(select(Book)).all()
        for b in books:
            job = Job(
                author_id=b.author_id,
                book_id=b.id,
                kind=JobKind.ingest_book,
                status=JobStatus.queued,
                job_data={"scheduled": True},
            )
            db.add(job)
            db.commit()
            db.refresh(job)
            run_ingest_job.delay(str(job.id))
    finally:
        db.close()
