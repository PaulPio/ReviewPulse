"""
Observability and cost metrics endpoint (N3, N12).

GET /metrics — returns system-level health + per-author cost breakdown.

This is the "debug at 3AM" panel described in N12. It surfaces:
  - Pipeline health (books, reviews, analyzed %, jobs by status)
  - LLM cost breakdown by book and by provider (N3)
  - AI-flagged review rate (potential quality signal)
  - Embedding coverage (semantic search completeness)

Cost figures are divided by 1_000_000 to convert from stored micros to USD.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_author
from app.db.base import get_db
from app.models.author import Author
from app.models.book import Book
from app.models.llm_usage import LLMUsage
from app.models.review import Review
from app.models.ingestion_job import IngestionJob

router = APIRouter()


@router.get("")
async def get_metrics(
    current_author: Author = Depends(get_current_author),
    db: AsyncSession = Depends(get_db),
):
    """
    Observability dashboard panel.

    Returns pipeline health stats + LLM cost breakdown scoped to the
    authenticated author. Safe to call frequently — read-only queries.
    """
    # --- Pipeline health ---
    books_count = (
        await db.execute(
            select(func.count(Book.id)).where(Book.author_id == current_author.id)
        )
    ).scalar() or 0

    reviews_count = (
        await db.execute(
            select(func.count(Review.id)).where(Review.author_id == current_author.id)
        )
    ).scalar() or 0

    analyzed_count = (
        await db.execute(
            select(func.count(Review.id)).where(
                Review.author_id == current_author.id,
                Review.sentiment.isnot(None),
            )
        )
    ).scalar() or 0

    embedded_count = (
        await db.execute(
            select(func.count(Review.id)).where(
                Review.author_id == current_author.id,
                Review.embedding.isnot(None),
            )
        )
    ).scalar() or 0

    ai_flagged_count = (
        await db.execute(
            select(func.count(Review.id)).where(
                Review.author_id == current_author.id,
                Review.is_ai_generated == True,  # noqa: E712
            )
        )
    ).scalar() or 0

    jobs_result = await db.execute(
        select(IngestionJob.status, func.count(IngestionJob.id))
        .where(IngestionJob.author_id == current_author.id)
        .group_by(IngestionJob.status)
    )
    jobs_by_status = dict(jobs_result.all())

    # --- LLM cost breakdown (N3) ---
    total_cost_micros = (
        await db.execute(
            select(func.sum(LLMUsage.cost_usd_micros)).where(
                LLMUsage.author_id == current_author.id
            )
        )
    ).scalar() or 0

    total_tokens = (
        await db.execute(
            select(func.sum(LLMUsage.total_tokens)).where(
                LLMUsage.author_id == current_author.id
            )
        )
    ).scalar() or 0

    # Cost by book
    cost_by_book_result = await db.execute(
        select(
            Book.id,
            Book.title,
            func.sum(LLMUsage.cost_usd_micros).label("cost_micros"),
            func.sum(LLMUsage.total_tokens).label("tokens"),
        )
        .join(LLMUsage, LLMUsage.book_id == Book.id, isouter=True)
        .where(Book.author_id == current_author.id)
        .group_by(Book.id, Book.title)
        .order_by(func.sum(LLMUsage.cost_usd_micros).desc())
    )
    cost_by_book = [
        {
            "book_id": str(row.id),
            "book_title": row.title,
            "cost_usd": round((row.cost_micros or 0) / 1_000_000, 6),
            "tokens": row.tokens or 0,
        }
        for row in cost_by_book_result.all()
    ]

    # Cost by provider
    cost_by_provider_result = await db.execute(
        select(
            LLMUsage.provider,
            func.sum(LLMUsage.cost_usd_micros).label("cost_micros"),
            func.sum(LLMUsage.total_tokens).label("tokens"),
            func.count(LLMUsage.id).label("calls"),
        )
        .where(LLMUsage.author_id == current_author.id)
        .group_by(LLMUsage.provider)
        .order_by(func.sum(LLMUsage.cost_usd_micros).desc())
    )
    cost_by_provider = [
        {
            "provider": row.provider,
            "cost_usd": round((row.cost_micros or 0) / 1_000_000, 6),
            "tokens": row.tokens or 0,
            "api_calls": row.calls,
        }
        for row in cost_by_provider_result.all()
    ]

    analysis_pct = round(analyzed_count / reviews_count * 100, 1) if reviews_count else 0
    embedding_pct = round(embedded_count / reviews_count * 100, 1) if reviews_count else 0
    ai_flagged_pct = round(ai_flagged_count / analyzed_count * 100, 1) if analyzed_count else 0

    return {
        "data": {
            "pipeline": {
                "total_books": books_count,
                "total_reviews": reviews_count,
                "analyzed_reviews": analyzed_count,
                "analysis_coverage_pct": analysis_pct,
                "embedded_reviews": embedded_count,
                "embedding_coverage_pct": embedding_pct,
                "ai_flagged_count": ai_flagged_count,
                "ai_flagged_rate_pct": ai_flagged_pct,
                "jobs_by_status": jobs_by_status,
            },
            "llm_cost": {
                "total_cost_usd": round(total_cost_micros / 1_000_000, 6),
                "total_tokens": total_tokens,
                "by_book": cost_by_book,
                "by_provider": cost_by_provider,
            },
        }
    }
