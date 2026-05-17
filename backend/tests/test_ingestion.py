"""
Integration test for the ingest → analyse → store happy path (N6).

This test exercises the full pipeline but mocks all external I/O:
- LLM calls (analyze_review, generate_synthetic_reviews)
- Embedding calls (embed_text)

The database interactions run against a real test DB (via conftest.py),
so constraints, uniqueness, and SQL behaviour are all tested for real.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book import Book
from app.models.ingestion_job import IngestionJob
from app.models.review import Review
from app.tasks.ingestion import _run_pipeline


def _make_synthetic_reviews(n: int = 3) -> list[dict]:
    """Generate n fake review dicts for mocking generate_synthetic_reviews."""
    return [
        {
            "external_id": f"syn-{i:04d}",
            "reviewer_name": f"Reviewer {i}",
            "rating": (i % 5) + 1,
            "title": f"Review title {i}",
            "body": f"This is a detailed review number {i} with enough text to be meaningful.",
            "review_date": datetime(2026, 4, 1 + i, tzinfo=timezone.utc),
            "verified_purchase": i % 2 == 0,
            "source": "synthetic",
        }
        for i in range(n)
    ]


_MOCK_ANALYSIS = {
    "sentiment": "positive",
    "sentiment_confidence": 0.88,
    "themes": ["characters", "pacing"],
    "is_ai_generated": False,
    "ai_generated_confidence": 0.06,
    "summary": "Mock summary.",
    "is_actionable": False,
    "actionable_reason": None,
}


@pytest.mark.asyncio
async def test_ingestion_happy_path(db: AsyncSession, author, book: Book):
    """
    Full pipeline: generate → insert → analyse → store.

    Verifies:
    - Reviews are inserted with correct book/author FK
    - Analysis fields are populated on Review rows
    - IngestionJob ends with status='completed'
    - LLMUsage rows are created
    """
    from app.services.analysis import AnalysisResult
    from app.services.llm.base import LLMResponse

    # Create a job
    job = IngestionJob(
        id=uuid.uuid4(),
        book_id=book.id,
        author_id=author.id,
        status="queued",
    )
    db.add(job)
    await db.flush()

    mock_analysis_result = AnalysisResult.model_validate(_MOCK_ANALYSIS)
    mock_llm_response = LLMResponse(
        content="",
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150,
        model="claude-3-5-haiku-20241022",
        provider="anthropic",
    )
    mock_synthetic = _make_synthetic_reviews(3)

    with (
        patch(
            "app.tasks.ingestion.generate_synthetic_reviews",
            new=AsyncMock(return_value=mock_synthetic),
        ),
        patch(
            "app.tasks.ingestion.analyze_review",
            new=AsyncMock(return_value=(mock_analysis_result, mock_llm_response)),
        ),
        patch(
            "app.tasks.ingestion.embed_text",
            new=AsyncMock(return_value=([0.1] * 1536, 50, 100)),
        ),
        patch("app.tasks.ingestion.deliver_webhook"),
    ):
        # Run in-process (no Celery worker needed)
        result = await _run_pipeline(
            job_id=str(job.id),
            celery_task_id="test-celery-id",
        )

    assert result["status"] == "completed"
    assert result["processed"] == 3
    assert result["failed"] == 0

    # Verify reviews were stored
    reviews_q = await db.execute(
        select(Review).where(Review.book_id == book.id)
    )
    reviews = list(reviews_q.scalars().all())
    assert len(reviews) == 3

    for r in reviews:
        assert r.sentiment == "positive"
        assert r.sentiment_confidence == 0.88
        assert r.analyzed_at is not None
        assert r.embedding is not None
        assert len(r.embedding) == 1536

    # Verify job status
    await db.refresh(job)
    assert job.status == "completed"
    assert job.processed_reviews == 3
    assert job.failed_reviews == 0


@pytest.mark.asyncio
async def test_ingestion_idempotency(db: AsyncSession, author, book: Book):
    """
    Running the same job twice must not create duplicate reviews.

    The ON CONFLICT DO NOTHING constraint ensures idempotency.
    LLM analysis is only run for reviews with analyzed_at IS NULL.
    """
    from app.services.analysis import AnalysisResult
    from app.services.llm.base import LLMResponse

    mock_analysis_result = AnalysisResult.model_validate(_MOCK_ANALYSIS)
    mock_llm_response = LLMResponse(
        content="",
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150,
        model="claude-3-5-haiku-20241022",
        provider="anthropic",
    )
    mock_synthetic = _make_synthetic_reviews(2)

    for _run in range(2):
        job = IngestionJob(
            id=uuid.uuid4(),
            book_id=book.id,
            author_id=author.id,
            status="queued",
        )
        db.add(job)
        await db.flush()

        with (
            patch(
                "app.tasks.ingestion.generate_synthetic_reviews",
                new=AsyncMock(return_value=mock_synthetic),
            ),
            patch(
                "app.tasks.ingestion.analyze_review",
                new=AsyncMock(return_value=(mock_analysis_result, mock_llm_response)),
            ),
            patch(
                "app.tasks.ingestion.embed_text",
                new=AsyncMock(return_value=([0.1] * 1536, 50, 100)),
            ),
            patch("app.tasks.ingestion.deliver_webhook"),
        ):
            await _run_pipeline(
                job_id=str(job.id),
                celery_task_id=f"test-run-{_run}",
            )

    # Should still only have 2 reviews, not 4
    reviews_q = await db.execute(
        select(Review).where(Review.book_id == book.id)
    )
    reviews = list(reviews_q.scalars().all())
    assert len(reviews) == 2, f"Expected 2 reviews (idempotent), got {len(reviews)}"


@pytest.mark.asyncio
async def test_ingestion_partial_failure(db: AsyncSession, author, book: Book):
    """
    If some reviews fail analysis, job ends as 'partial' (not 'failed').
    Successful reviews are still stored.
    """
    from app.services.analysis import AnalysisResult
    from app.services.llm.base import LLMResponse, LLMError

    mock_analysis_result = AnalysisResult.model_validate(_MOCK_ANALYSIS)
    mock_llm_response = LLMResponse(
        content="",
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150,
        model="claude-3-5-haiku-20241022",
        provider="anthropic",
    )
    mock_synthetic = _make_synthetic_reviews(3)

    call_count = 0

    async def mock_analyze(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 2:  # fail the second review
            raise LLMError("Simulated failure", provider="anthropic")
        return mock_analysis_result, mock_llm_response

    job = IngestionJob(
        id=uuid.uuid4(),
        book_id=book.id,
        author_id=author.id,
        status="queued",
    )
    db.add(job)
    await db.flush()

    with (
        patch(
            "app.tasks.ingestion.generate_synthetic_reviews",
            new=AsyncMock(return_value=mock_synthetic),
        ),
        patch("app.tasks.ingestion.analyze_review", new=mock_analyze),
        patch(
            "app.tasks.ingestion.embed_text",
            new=AsyncMock(return_value=([0.1] * 1536, 50, 100)),
        ),
        patch("app.tasks.ingestion.deliver_webhook"),
    ):
        result = await _run_pipeline(
            job_id=str(job.id),
            celery_task_id="test-partial",
        )

    assert result["status"] == "partial"
    assert result["processed"] == 2
    assert result["failed"] == 1

    await db.refresh(job)
    assert job.status == "partial"
    assert job.error_details is not None
    assert len(job.error_details) == 1
