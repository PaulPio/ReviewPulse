"""
Trend analytics, comparison, whats-new, digest, and audience insights endpoints.

Endpoints
---------
GET  /books/{book_id}/trends          — weekly sentiment timeline (F5)
GET  /books/{book_id}/trends/themes   — theme frequency breakdown (F5)
POST /compare                          — side-by-side book comparison (F6)
GET  /whats-new                        — activity since last login (F8)
GET  /digest                           — weekly digest preview (F10)
GET  /audience-insights                — P1: reader segment clustering

P1 — Audience Insights
----------------------
Gap not in the spec: authors have no visibility into WHO is reviewing their books.
Are they superfans who review every book? Casual readers who write one sentence?
Literary critics who dissect craft? Knowing the segment mix tells an author
whether to invest in series continuity, prose quality, or discoverability.

We cluster by review length + themes present (heuristic; real k-means clustering
would require the embedding vectors and is marked as a future enhancement).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, case, extract
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_author
from app.db.base import get_db
from app.models.author import Author
from app.models.book import Book
from app.models.review import Review
from app.services.audience import get_audience_insights

router = APIRouter()


@router.get("/books/{book_id}/trends")
async def get_trends(
    book_id: uuid.UUID,
    current_author: Author = Depends(get_current_author),
    db: AsyncSession = Depends(get_db),
):
    # Verify book ownership
    book_result = await db.execute(
        select(Book).where(Book.id == book_id, Book.author_id == current_author.id)
    )
    if not book_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Book not found")

    # Weekly sentiment timeline (last 12 weeks)
    twelve_weeks_ago = datetime.now(timezone.utc) - timedelta(weeks=12)

    result = await db.execute(
        select(
            func.date_trunc("week", Review.review_date).label("period_start"),
            func.count(Review.id).filter(Review.sentiment == "positive").label("positive"),
            func.count(Review.id).filter(Review.sentiment == "mixed").label("mixed"),
            func.count(Review.id).filter(Review.sentiment == "negative").label("negative"),
            func.count(Review.id).label("total"),
        )
        .where(
            Review.book_id == book_id,
            Review.author_id == current_author.id,
            Review.review_date >= twelve_weeks_ago,
            Review.sentiment.isnot(None),
        )
        .group_by(func.date_trunc("week", Review.review_date))
        .order_by(func.date_trunc("week", Review.review_date))
    )

    timeline = [
        {
            "period_start": row.period_start.isoformat() if row.period_start else None,
            "positive": row.positive,
            "mixed": row.mixed,
            "negative": row.negative,
            "total": row.total,
        }
        for row in result.all()
    ]

    return {"data": timeline}


@router.get("/books/{book_id}/trends/themes")
async def get_theme_breakdown(
    book_id: uuid.UUID,
    current_author: Author = Depends(get_current_author),
    db: AsyncSession = Depends(get_db),
):
    # Get all reviews with themes
    result = await db.execute(
        select(Review.themes)
        .where(
            Review.book_id == book_id,
            Review.author_id == current_author.id,
            Review.themes.isnot(None),
        )
    )

    # Count themes
    theme_counts: dict[str, int] = {}
    for (themes,) in result.all():
        if themes:
            for theme in themes:
                theme_counts[theme] = theme_counts.get(theme, 0) + 1

    # Sort by count, return top 10
    sorted_themes = sorted(theme_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    return {"data": [{"theme": t, "count": c} for t, c in sorted_themes]}


@router.post("/compare")
async def compare_books(
    body: dict,
    current_author: Author = Depends(get_current_author),
    db: AsyncSession = Depends(get_db),
):
    book_ids = body.get("book_ids", [])
    if len(book_ids) < 2 or len(book_ids) > 10:
        raise HTTPException(status_code=400, detail="Select 2-10 books to compare")

    # Verify all books belong to author
    result = await db.execute(
        select(Book).where(Book.author_id == current_author.id, Book.id.in_(book_ids))
    )
    books = result.scalars().all()
    if len(books) != len(book_ids):
        raise HTTPException(status_code=404, detail="One or more books not found")

    comparisons = []
    for book in books:
        stats = await db.execute(
            select(
                func.count(Review.id).label("total"),
                func.count(Review.id).filter(Review.sentiment == "positive").label("positive"),
                func.count(Review.id).filter(Review.sentiment == "mixed").label("mixed"),
                func.count(Review.id).filter(Review.sentiment == "negative").label("negative"),
                func.avg(Review.rating).label("avg_rating"),
            ).where(Review.book_id == book.id)
        )
        row = stats.one()
        comparisons.append({
            "book_id": str(book.id),
            "title": book.title,
            "total_reviews": row.total,
            "sentiment_distribution": {
                "positive": row.positive,
                "mixed": row.mixed,
                "negative": row.negative,
            },
            "avg_rating": round(row.avg_rating, 2) if row.avg_rating else None,
        })

    return {"data": comparisons}


@router.get("/whats-new")
async def whats_new(
    current_author: Author = Depends(get_current_author),
    db: AsyncSession = Depends(get_db),
):
    since = current_author.last_login_at or (datetime.now(timezone.utc) - timedelta(days=7))

    # New reviews since last login
    new_reviews_result = await db.execute(
        select(func.count(Review.id))
        .where(Review.author_id == current_author.id, Review.created_at > since)
    )
    new_count = new_reviews_result.scalar() or 0

    # Actionable reviews
    actionable_result = await db.execute(
        select(Review)
        .where(
            Review.author_id == current_author.id,
            Review.created_at > since,
            Review.is_actionable == True,
        )
        .limit(5)
    )
    actionable = actionable_result.scalars().all()

    # AI-flagged reviews
    ai_flagged_result = await db.execute(
        select(Review)
        .where(
            Review.author_id == current_author.id,
            Review.created_at > since,
            Review.is_ai_generated == True,
        )
        .limit(5)
    )
    ai_flagged = ai_flagged_result.scalars().all()

    return {
        "new_reviews_count": new_count,
        "since": since.isoformat(),
        "actionable_reviews": [
            {"id": str(r.id), "book_id": str(r.book_id), "summary": r.summary, "rating": r.rating}
            for r in actionable
        ],
        "ai_flagged_reviews": [
            {"id": str(r.id), "book_id": str(r.book_id), "summary": r.summary, "rating": r.rating}
            for r in ai_flagged
        ],
    }


_DIGEST_PERIOD_DAYS = 90


def _sentiment_trend(pos: int, total: int, prior_pos: int, prior_total: int) -> str:
    this_pct  = round(pos / total * 100)            if total       > 0 else 0
    prior_pct = round(prior_pos / prior_total * 100) if prior_total > 0 else 0
    if this_pct > prior_pct + 5:
        return "improving"
    if this_pct < prior_pct - 5:
        return "declining"
    return "stable"


def _ai_alert(ai_flagged: int, total: int) -> str | None:
    rate = round(ai_flagged / total * 100, 1) if total else 0
    if rate > 15:
        return (
            f"{rate}% of recent reviews appear AI-generated — "
            "consider reporting flagged reviews to Amazon."
        )
    return None


async def _book_digest_entry(
    book: Book,
    db: AsyncSession,
    period_start: datetime,
    prior_start: datetime,
) -> dict | None:
    bstats = await db.execute(
        select(
            func.count(Review.id).label("total"),
            func.count(Review.id).filter(Review.sentiment == "positive").label("positive"),
            func.count(Review.id).filter(Review.is_actionable == True).label("actionable"),  # noqa: E712
            func.count(Review.id).filter(Review.is_ai_generated == True).label("ai_flagged"),  # noqa: E712
        ).where(
            Review.book_id == book.id,
            Review.review_date >= period_start,
            Review.sentiment.isnot(None),
        )
    )
    brow = bstats.one()
    total = brow.total or 0
    if total == 0:
        return None

    pstats = await db.execute(
        select(
            func.count(Review.id).label("total"),
            func.count(Review.id).filter(Review.sentiment == "positive").label("positive"),
        ).where(
            Review.book_id == book.id,
            Review.review_date >= prior_start,
            Review.review_date < period_start,
            Review.sentiment.isnot(None),
        )
    )
    prow = pstats.one()

    actionable_q = await db.execute(
        select(Review.actionable_reason)
        .where(
            Review.book_id == book.id,
            Review.review_date >= period_start,
            Review.is_actionable == True,  # noqa: E712
            Review.actionable_reason.isnot(None),
        )
        .limit(3)
    )
    actionable_reasons = [r for (r,) in actionable_q.all() if r]

    pos = brow.positive or 0
    pos_pct = round(pos / total * 100)

    return {
        "book_id": str(book.id),
        "book_title": book.title,
        "sentiment_summary": (
            f"{pos_pct}% positive ({pos}/{total} reviews in last {_DIGEST_PERIOD_DAYS} days)"
        ),
        "overall_sentiment_trend": _sentiment_trend(pos, total, prow.positive or 0, prow.total or 0),
        "actionable_highlights": actionable_reasons,
        "ai_flagged_alert": _ai_alert(brow.ai_flagged or 0, total),
    }


@router.get("/digest")
async def weekly_digest(
    current_author: Author = Depends(get_current_author),
    db: AsyncSession = Depends(get_db),
):
    """Weekly digest preview (F10). Uses review_date so seeded demo data is always visible."""
    now          = datetime.now(timezone.utc)
    period_start = now - timedelta(days=_DIGEST_PERIOD_DAYS)
    prior_start  = now - timedelta(days=_DIGEST_PERIOD_DAYS * 2)

    books_result = await db.execute(
        select(Book).where(Book.author_id == current_author.id)
    )
    books = books_result.scalars().all()

    book_sections = []
    for book in books:
        entry = await _book_digest_entry(book, db, period_start, prior_start)
        if entry:
            book_sections.append(entry)

    return {
        "generated_at": now.isoformat(),
        "books": book_sections,
    }


@router.get("/audience-insights")
async def audience_insights(
    current_author: Author = Depends(get_current_author),
    db: AsyncSession = Depends(get_db),
):
    """
    P1 Feature: Reader Audience Segmentation.

    Clusters reviewers into segments based on their review patterns.
    This surfaces who is actually reading the author's books:
      - Casual Readers: short reviews, focus on entertainment
      - Literary Critics: long, craft-focused reviews
      - Series Enthusiasts: recurring reviewers with strong opinions

    Justification: Amazon's own analytics don't surface audience segmentation.
    An author knowing that 60% of their readers are casual readers should
    invest in hooky openings and emotional payoffs, not prose complexity.
    Knowing they have a growing literary-critic segment suggests the writing
    quality is resonating and they can lean into more ambitious projects.

    Future enhancement: use k-means on embedding vectors for true semantic
    clustering rather than heuristic length/theme rules.
    """
    segments = await get_audience_insights(current_author.id, db)
    total_reviewers = sum(s["count"] for s in segments)

    for segment in segments:
        segment["percentage"] = (
            round(segment["count"] / total_reviewers * 100, 1) if total_reviewers > 0 else 0
        )

    return {
        "data": {
            "segments": segments,
            "total_reviewers_analysed": total_reviewers,
            "insight": (
                "Segments are based on review length and theme patterns. "
                "A future version will use embedding-based k-means clustering "
                "for more accurate segmentation."
            ),
        }
    }
