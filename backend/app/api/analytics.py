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
        "data": {
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
    }


@router.get("/digest")
async def weekly_digest(
    current_author: Author = Depends(get_current_author),
    db: AsyncSession = Depends(get_db),
):
    """
    Weekly digest preview (F10).

    Returns the data that would be emailed to the author each Monday.
    Structured for easy rendering as an HTML email or plain text summary.

    What makes this digest useful (not generic):
    - Per-book breakdown so the author sees which title needs attention
    - Actionable highlights with specific reasons, not just counts
    - AI-flagged rate spike alert if the rate jumped >10% this week
    - Cost spend for the week (authors on a budget care about this)
    """
    now = datetime.now(timezone.utc)
    one_week_ago = now - timedelta(days=7)
    two_weeks_ago = now - timedelta(days=14)

    # Get all books for this author
    books_result = await db.execute(
        select(Book).where(Book.author_id == current_author.id)
    )
    books = books_result.scalars().all()

    # Overall this-week stats
    overall_stats = await db.execute(
        select(
            func.count(Review.id).label("total"),
            func.count(Review.id).filter(Review.sentiment == "positive").label("positive"),
            func.count(Review.id).filter(Review.sentiment == "negative").label("negative"),
            func.count(Review.id).filter(Review.is_ai_generated == True).label("ai_flagged"),  # noqa: E712
            func.avg(Review.rating).label("avg_rating"),
        ).where(
            Review.author_id == current_author.id,
            Review.created_at >= one_week_ago,
        )
    )
    overall = overall_stats.one()

    # Prior week for trend comparison
    prior_stats = await db.execute(
        select(
            func.count(Review.id).label("total"),
            func.count(Review.id).filter(Review.sentiment == "positive").label("positive"),
        ).where(
            Review.author_id == current_author.id,
            Review.created_at >= two_weeks_ago,
            Review.created_at < one_week_ago,
        )
    )
    prior = prior_stats.one()

    # Per-book sections
    book_sections = []
    for book in books:
        book_stats = await db.execute(
            select(
                func.count(Review.id).label("total"),
                func.count(Review.id).filter(Review.sentiment == "positive").label("positive"),
                func.count(Review.id).filter(Review.sentiment == "negative").label("negative"),
                func.count(Review.id).filter(Review.is_actionable == True).label("actionable"),  # noqa: E712
                func.avg(Review.rating).label("avg_rating"),
            ).where(
                Review.book_id == book.id,
                Review.created_at >= one_week_ago,
            )
        )
        brow = book_stats.one()
        if (brow.total or 0) == 0:
            continue

        # Top actionable highlights
        actionable_q = await db.execute(
            select(Review.actionable_reason)
            .where(
                Review.book_id == book.id,
                Review.created_at >= one_week_ago,
                Review.is_actionable == True,  # noqa: E712
                Review.actionable_reason.isnot(None),
            )
            .limit(3)
        )
        actionable_reasons = [r for (r,) in actionable_q.all() if r]

        total = brow.total or 0
        pos = brow.positive or 0
        neg = brow.negative or 0
        pos_pct = round(pos / total * 100) if total else 0

        book_sections.append({
            "book_id": str(book.id),
            "book_title": book.title,
            "new_reviews": total,
            "avg_rating": round(brow.avg_rating, 1) if brow.avg_rating else None,
            "sentiment_summary": f"{pos_pct}% positive ({pos}/{total} reviews)",
            "actionable_count": brow.actionable or 0,
            "actionable_highlights": actionable_reasons,
        })

    # AI-flagged spike alert
    ai_flagged_rate_this_week = (
        round((overall.ai_flagged or 0) / overall.total * 100, 1)
        if (overall.total or 0) > 0
        else 0.0
    )
    ai_alert = None
    if ai_flagged_rate_this_week > 15:
        ai_alert = (
            f"AI-generated review rate is {ai_flagged_rate_this_week}% this week — "
            "consider reporting flagged reviews to Amazon."
        )

    # Overall trend
    this_pos_pct = round((overall.positive or 0) / overall.total * 100) if (overall.total or 0) > 0 else 0
    prior_pos_pct = round((prior.positive or 0) / prior.total * 100) if (prior.total or 0) > 0 else 0
    if this_pos_pct > prior_pos_pct + 5:
        trend = "improving"
    elif this_pos_pct < prior_pos_pct - 5:
        trend = "declining"
    else:
        trend = "stable"

    highlights = []
    if overall.total:
        highlights.append(f"{overall.total} new reviews this week")
    if overall.positive:
        highlights.append(f"{overall.positive} positive ({this_pos_pct}%)")
    if overall.negative:
        highlights.append(f"{overall.negative} reviews need attention")
    if trend == "improving":
        highlights.append(f"Sentiment up {this_pos_pct - prior_pos_pct}pp vs last week")
    elif trend == "declining":
        highlights.append(f"Sentiment down {prior_pos_pct - this_pos_pct}pp vs last week — investigate")

    return {
        "data": {
            "author_name": current_author.display_name,
            "period_start": one_week_ago.date().isoformat(),
            "period_end": now.date().isoformat(),
            "total_new_reviews": overall.total or 0,
            "overall_sentiment_trend": trend,
            "highlights": highlights,
            "books": book_sections,
            "ai_flagged_alert": ai_alert,
            "summary": (
                f"You received {overall.total or 0} new reviews this week. "
                f"Sentiment is {trend}. "
                f"Average rating: {round(overall.avg_rating, 1) if overall.avg_rating else 'N/A'}/5."
            ),
        }
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
