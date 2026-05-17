"""Review ingestion service - loads reviews from seed data or external sources."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book import Book
from app.models.review import Review

logger = structlog.get_logger()

SEED_DATA_PATH = Path(__file__).parent.parent.parent / "data" / "seed_reviews.json"


async def ingest_reviews_for_book(book_id: uuid.UUID, author_id: uuid.UUID, db: AsyncSession) -> int:
    """Ingest reviews for a book from seed data. Returns number of new reviews added."""
    book = await db.get(Book, book_id)
    if not book:
        return 0

    # Load seed data
    if not SEED_DATA_PATH.exists():
        logger.warning("seed_data_not_found", path=str(SEED_DATA_PATH))
        return 0

    with open(SEED_DATA_PATH) as f:
        all_reviews = json.load(f)

    # Filter reviews for this book (by title match)
    book_reviews = [r for r in all_reviews if r.get("book_title", "").lower() == book.title.lower()]

    new_count = 0
    for review_data in book_reviews:
        external_id = review_data.get("review_id", str(uuid.uuid4()))

        # Check idempotency
        existing = await db.execute(
            select(Review).where(
                Review.book_id == book_id,
                Review.external_id == external_id,
            )
        )
        if existing.scalar_one_or_none():
            continue

        review = Review(
            id=uuid.uuid4(),
            book_id=book_id,
            author_id=author_id,
            external_id=external_id,
            reviewer_name=review_data.get("reviewer_name"),
            rating=review_data.get("rating"),
            title=review_data.get("review_summary"),
            body=review_data.get("review_text", ""),
            review_date=datetime.fromisoformat(review_data["review_date"]) if review_data.get("review_date") else datetime.now(timezone.utc),
            verified_purchase=review_data.get("verified_purchase", False),
            source="seed",
        )
        db.add(review)
        new_count += 1

    await db.flush()
    logger.info("reviews_ingested", book_id=str(book_id), new_count=new_count)
    return new_count
