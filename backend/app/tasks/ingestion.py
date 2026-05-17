"""
Celery tasks for the ingest + analyse pipeline.

Pipeline per book
-----------------
1. `run_ingestion_job(job_id)`
   a. Load the IngestionJob and Book from DB
   b. Generate (or fetch) reviews → insert with ON CONFLICT DO NOTHING (idempotent)
   c. For each unanalysed review:
      - Call `analyze_review()` (LLM)
      - Embed the review body
      - Update the Review row with analysis + embedding
      - Record LLMUsage rows (N3)
   d. Mark job completed/partial/failed
   e. Fire webhook (N10)

Idempotency (F11)
-----------------
Reviews are inserted with `INSERT ... ON CONFLICT (book_id, external_id) DO NOTHING`.
LLM analysis only runs for reviews where `analyzed_at IS NULL`, so re-running
the same job is safe and cheap.

Partial failure (F2)
--------------------
Individual review failures increment `failed_reviews` but don't abort the job.
The job ends as "partial" if any reviews failed, "completed" if all succeeded.

Observability (N4)
------------------
Every step logs `{review_id, book_id, job_id, step, error}` via structlog.
The error_details JSONB column on IngestionJob accumulates per-review errors
so the dashboard can show "12/50 processed, 2 failed: [details]".
"""

from __future__ import annotations

import asyncio
import time
import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import insert, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.logging import get_logger
from app.db.base import AsyncSessionLocal
from app.models.ingestion_job import IngestionJob
from app.models.book import Book
from app.models.review import Review
from app.models.llm_usage import LLMUsage
from app.services.analysis import analyze_review
from app.services.embedding import embed_text
from app.services.synthetic import generate_synthetic_reviews
from app.services.llm.base import LLMError, calculate_cost_usd_micros
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(bind=True, max_retries=0, name="app.tasks.ingestion.run_ingestion_job")
def run_ingestion_job(self, job_id: str) -> dict[str, Any]:
    """
    Entry point for the ingestion pipeline.

    Celery tasks are sync; we run the async pipeline via asyncio.run().
    This is the standard pattern for Celery + async SQLAlchemy.
    """
    return asyncio.run(_run_pipeline(job_id=job_id, celery_task_id=self.request.id))


async def _run_pipeline(job_id: str, celery_task_id: str) -> dict[str, Any]:
    """Async implementation of the ingestion pipeline."""
    async with AsyncSessionLocal() as db:
        # --- 1. Load job ---
        job = await db.get(IngestionJob, UUID(job_id))
        if not job:
            logger.error("ingestion.job_not_found", job_id=job_id)
            return {"status": "failed", "reason": "job not found"}

        book = await db.get(Book, job.book_id)
        if not book:
            await _fail_job(db, job, "book not found")
            return {"status": "failed"}

        # --- 2. Mark running ---
        job.status = "running"
        job.started_at = datetime.now(timezone.utc)
        job.celery_task_id = celery_task_id
        await db.commit()
        t_start = time.perf_counter()

        logger.info(
            "ingestion.started",
            job_id=job_id,
            book_id=str(book.id),
            book_title=book.title,
        )

        # --- 3. Generate / fetch reviews ---
        try:
            raw_reviews = await generate_synthetic_reviews(
                book_id=str(book.id),
                book_title=book.title,
                author_name="",  # not needed for prompt quality
            )
        except Exception as exc:
            logger.error("ingestion.fetch_failed", job_id=job_id, error=str(exc))
            await _fail_job(db, job, str(exc))
            return {"status": "failed"}
        t_after_generate = time.perf_counter()

        # --- 4. Bulk-insert with idempotency ---
        inserted_count = 0
        for r in raw_reviews:
            stmt = (
                pg_insert(Review)
                .values(
                    book_id=book.id,
                    author_id=book.author_id,
                    external_id=r["external_id"],
                    reviewer_name=r.get("reviewer_name"),
                    rating=r.get("rating"),
                    title=r.get("title"),
                    body=r["body"],
                    review_date=r.get("review_date"),
                    verified_purchase=r.get("verified_purchase", False),
                    source=r.get("source", "synthetic"),
                )
                .on_conflict_do_nothing(constraint="uq_reviews_book_external")
            )
            result = await db.execute(stmt)
            inserted_count += result.rowcount or 0

        await db.commit()
        t_after_insert = time.perf_counter()

        logger.info(
            "ingestion.reviews_inserted",
            job_id=job_id,
            inserted=inserted_count,
            total_raw=len(raw_reviews),
        )

        # --- 5. Analyse unprocessed reviews ---
        unanalysed_q = select(Review).where(
            Review.book_id == book.id,
            Review.analyzed_at.is_(None),
        )
        result = await db.execute(unanalysed_q)
        unanalysed: list[Review] = list(result.scalars().all())

        job.total_reviews = len(unanalysed)
        job.processed_reviews = 0
        job.failed_reviews = 0
        await db.commit()

        error_details: list[dict] = []

        for review in unanalysed:
            t_rev_start = time.perf_counter()
            try:
                analysis, llm_resp = await analyze_review(
                    review_body=review.body,
                    book_title=book.title,
                    reviewer_name=review.reviewer_name,
                    rating=review.rating,
                )

                # Embed
                try:
                    embedding, embed_tokens, embed_cost = await embed_text(review.body)
                    review.embedding = embedding
                    # Record embedding usage
                    embed_usage = LLMUsage(
                        author_id=book.author_id,
                        book_id=book.id,
                        review_id=review.id,
                        provider="openai",
                        model="text-embedding-3-small",
                        operation="embed_review",
                        prompt_tokens=embed_tokens,
                        completion_tokens=0,
                        total_tokens=embed_tokens,
                        cost_usd_micros=embed_cost,
                    )
                    db.add(embed_usage)
                except Exception as embed_exc:
                    logger.warning(
                        "ingestion.embed_failed",
                        review_id=str(review.id),
                        error=str(embed_exc),
                    )

                # Apply analysis
                review.sentiment = analysis.sentiment
                review.sentiment_confidence = analysis.sentiment_confidence
                review.themes = analysis.themes
                review.is_ai_generated = analysis.is_ai_generated
                review.ai_generated_confidence = analysis.ai_generated_confidence
                review.summary = analysis.summary
                review.is_actionable = analysis.is_actionable
                review.actionable_reason = analysis.actionable_reason
                review.analysis_raw = {
                    "sentiment": analysis.sentiment,
                    "themes": analysis.themes,
                    "provider": llm_resp.provider,
                    "model": llm_resp.model,
                }
                review.analyzed_at = datetime.now(timezone.utc)

                # Record LLM usage
                cost_micros, pricing = calculate_cost_usd_micros(
                    provider=llm_resp.provider,
                    model=llm_resp.model,
                    prompt_tokens=llm_resp.prompt_tokens,
                    completion_tokens=llm_resp.completion_tokens,
                )
                usage = LLMUsage(
                    author_id=book.author_id,
                    book_id=book.id,
                    review_id=review.id,
                    provider=llm_resp.provider,
                    model=llm_resp.model,
                    operation="analyze_review",
                    prompt_tokens=llm_resp.prompt_tokens,
                    completion_tokens=llm_resp.completion_tokens,
                    total_tokens=llm_resp.total_tokens,
                    cost_usd_micros=cost_micros,
                    pricing_snapshot=pricing,
                )
                db.add(usage)

                job.processed_reviews += 1
                await db.commit()

                logger.info(
                    "ingestion.review_analysed",
                    job_id=job_id,
                    review_id=str(review.id),
                    sentiment=analysis.sentiment,
                )

            except Exception as exc:
                job.failed_reviews += 1
                error_details.append(
                    {
                        "review_id": str(review.id),
                        "external_id": review.external_id,
                        "error": str(exc),
                        "step": "analyze_review",
                    }
                )
                logger.error(
                    "ingestion.review_failed",
                    job_id=job_id,
                    review_id=str(review.id),
                    error=str(exc),
                )
                await db.commit()
            logger.debug(
                "ingestion.review_timing",
                job_id=job_id,
                review_id=str(review.id),
                elapsed_s=round(time.perf_counter() - t_rev_start, 2),
            )
        t_after_analysis = time.perf_counter()

        # --- 6. Finalise job ---
        job.completed_at = datetime.now(timezone.utc)
        job.error_details = error_details if error_details else None

        if job.failed_reviews == 0:
            job.status = "completed"
        elif job.processed_reviews == 0:
            job.status = "failed"
            job.error_message = "All reviews failed analysis"
        else:
            job.status = "partial"

        await db.commit()
        t_after_finalize = time.perf_counter()
        logger.info(
            "ingestion.timing",
            job_id=job_id,
            generate_s=round(t_after_generate - t_start, 2),
            insert_s=round(t_after_insert - t_after_generate, 2),
            analysis_s=round(t_after_analysis - t_after_insert, 2),
            finalize_s=round(t_after_finalize - t_after_analysis, 2),
            total_pipeline_s=round(t_after_finalize - t_start, 2),
        )

        logger.info(
            "ingestion.finished",
            job_id=job_id,
            status=job.status,
            processed=job.processed_reviews,
            failed=job.failed_reviews,
        )

        # --- 7. Fire webhook ---
        from app.tasks.webhook import deliver_webhook
        deliver_webhook.delay(
            job_id=job_id,
            author_id=str(book.author_id),
            status=job.status,
            processed=job.processed_reviews,
            failed=job.failed_reviews,
        )

        return {
            "status": job.status,
            "processed": job.processed_reviews,
            "failed": job.failed_reviews,
        }


async def _fail_job(db, job: IngestionJob, reason: str) -> None:
    job.status = "failed"
    job.error_message = reason
    job.completed_at = datetime.now(timezone.utc)
    await db.commit()
