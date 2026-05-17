"""P1 Feature: Reading Group Insights - cluster reviewers by patterns."""

from __future__ import annotations

import uuid
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.review import Review


async def get_audience_insights(author_id: uuid.UUID, db: AsyncSession) -> list[dict]:
    """Cluster reviewers into audience segments based on review patterns."""
    result = await db.execute(
        select(Review).where(
            Review.author_id == author_id,
            Review.sentiment.isnot(None),
        )
    )
    reviews = result.scalars().all()

    if not reviews:
        return []

    # Group by reviewer
    reviewer_data: dict[str, list] = defaultdict(list)
    for review in reviews:
        key = review.reviewer_name or "anonymous"
        reviewer_data[key].append(review)

    # Simple heuristic clustering based on review characteristics
    segments = {
        "casual_readers": {"name": "Casual Readers", "description": "Short reviews, focus on entertainment value", "reviewers": [], "avg_rating": 0, "common_themes": []},
        "literary_critics": {"name": "Literary Critics", "description": "Detailed reviews, focus on craft elements", "reviewers": [], "avg_rating": 0, "common_themes": []},
        "enthusiasts": {"name": "Series Enthusiasts", "description": "Frequent reviewers with strong opinions", "reviewers": [], "avg_rating": 0, "common_themes": []},
    }

    for reviewer_name, revs in reviewer_data.items():
        avg_length = sum(len(r.body) for r in revs) / len(revs)
        avg_rating = sum(r.rating for r in revs if r.rating) / max(1, sum(1 for r in revs if r.rating))

        if avg_length < 200:
            segments["casual_readers"]["reviewers"].append(reviewer_name)
        elif avg_length > 500 or any("writing_style" in (r.themes or []) or "pacing" in (r.themes or []) for r in revs):
            segments["literary_critics"]["reviewers"].append(reviewer_name)
        else:
            segments["enthusiasts"]["reviewers"].append(reviewer_name)

    # Calculate segment stats
    for segment in segments.values():
        segment["count"] = len(segment["reviewers"])
        segment.pop("reviewers")  # Don't expose individual names

    return [s for s in segments.values() if s["count"] > 0]
