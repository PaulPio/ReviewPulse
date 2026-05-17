"""
Synthetic review generator.

In the absence of a real Amazon scraper, this generates realistic book reviews
using the configured LLM. Reviews span multiple dates, sentiments, and themes
to give the trend/comparison analytics meaningful data to work with.

Idempotency (F11)
-----------------
Each synthetic review is assigned an external_id derived from:
    sha256(book_id + reviewer_name + review_date_iso)[:16]
This is deterministic so re-running the generator produces the same IDs,
and the (book_id, external_id) unique constraint prevents duplicates.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.logging import get_logger
from app.services.llm.factory import get_llm_client

logger = get_logger(__name__)

SYNTHETIC_SYSTEM = """You are generating realistic Amazon book reviews for testing purposes.
Return ONLY a valid JSON array of review objects. Each object must have:
- reviewer_name: string (realistic first name + last initial)
- rating: integer 1-5
- title: string (short review title, max 80 chars)
- body: string (review body, 50-300 words, natural tone)
- review_date: ISO 8601 date string (within the last 90 days)
- verified_purchase: boolean
- themes_hint: array of 1-3 themes the review touches (for realism diversity)

Mix of sentiments: roughly 60% positive, 25% mixed, 15% negative.
Vary dates across the last 90 days. Make reviews feel like real readers wrote them.
Return ONLY the JSON array."""


class SyntheticReviewRaw(BaseModel):
    reviewer_name: str
    rating: int = Field(ge=1, le=5)
    title: str
    body: str
    review_date: str
    verified_purchase: bool
    themes_hint: list[str] = Field(default_factory=list)


def _make_external_id(book_id: str, reviewer_name: str, review_date: str) -> str:
    raw = f"{book_id}:{reviewer_name}:{review_date}"
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


async def generate_synthetic_reviews(
    book_id: str,
    book_title: str,
    author_name: str,
    count: int | None = None,
) -> list[dict]:
    """
    Generate synthetic reviews for a book via LLM.

    Returns a list of dicts ready to bulk-insert as Review rows.
    """
    count = count or settings.synthetic_reviews_per_book
    client = get_llm_client()

    prompt = (
        f'Generate {count} realistic Amazon book reviews for the book "{book_title}" '
        f'by {author_name}. Vary the sentiments, themes, dates, and reviewer personas.'
    )

    logger.info("synthetic.generating", book_id=book_id, book_title=book_title, count=count)

    data, llm_resp = await client.complete_json(prompt=prompt, system=SYNTHETIC_SYSTEM)

    # `data` should be a list; handle edge case where model wraps it
    if isinstance(data, dict):
        data = data.get("reviews", data.get("items", []))

    reviews_out = []
    for raw in data:
        try:
            rev = SyntheticReviewRaw.model_validate(raw)
        except Exception as exc:
            logger.warning("synthetic.parse_error", error=str(exc), raw=raw)
            continue

        external_id = _make_external_id(book_id, rev.reviewer_name, rev.review_date)

        try:
            review_date = datetime.fromisoformat(rev.review_date.replace("Z", "+00:00"))
        except ValueError:
            review_date = datetime.now(timezone.utc) - timedelta(days=30)

        reviews_out.append(
            {
                "external_id": external_id,
                "reviewer_name": rev.reviewer_name,
                "rating": rev.rating,
                "title": rev.title,
                "body": rev.body,
                "review_date": review_date,
                "verified_purchase": rev.verified_purchase,
                "source": "synthetic",
            }
        )

    logger.info(
        "synthetic.complete",
        book_id=book_id,
        generated=len(reviews_out),
        tokens=llm_resp.total_tokens,
    )
    return reviews_out
