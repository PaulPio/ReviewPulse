"""Review listing with filters and pagination."""

from __future__ import annotations

import uuid
from math import ceil
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_author
from app.db.base import get_db
from app.models.author import Author
from app.models.book import Book
from app.models.review import Review
from app.schemas.review import ReviewFilter, ReviewOut, ReviewPage

router = APIRouter()

# Explicit allowlist — prevents arbitrary attribute injection via sort_by (R1).
# Keys mirror ReviewFilter.sort_by Literal; guaranteed valid after Pydantic validation.
_SORT_COLS = {
    "review_date": Review.review_date,
    "rating": Review.rating,
    "created_at": Review.created_at,
    "sentiment_confidence": Review.sentiment_confidence,
}


@router.get("/books/{book_id}/reviews", response_model=ReviewPage)
async def list_reviews(
    book_id: uuid.UUID,
    filters: Annotated[ReviewFilter, Query()],
    current_author: Author = Depends(get_current_author),
    db: AsyncSession = Depends(get_db),
):
    # R4 — 404 guard: returns 404 (not empty list) when book doesn't exist or
    # belongs to another author, avoiding information leakage about existence.
    book_result = await db.execute(
        select(Book).where(Book.id == book_id, Book.author_id == current_author.id)
    )
    if not book_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Book not found")

    base_query = select(Review).where(
        Review.book_id == book_id,
        Review.author_id == current_author.id,
    )

    # Apply filters — all validated by ReviewFilter (R2, R3).
    if filters.sentiment is not None:
        base_query = base_query.where(Review.sentiment == filters.sentiment)
    if filters.is_ai_generated is not None:
        base_query = base_query.where(Review.is_ai_generated == filters.is_ai_generated)
    if filters.is_actionable is not None:
        base_query = base_query.where(Review.is_actionable == filters.is_actionable)
    if filters.theme is not None:
        base_query = base_query.where(Review.themes.any(filters.theme))
    if filters.date_from is not None:
        base_query = base_query.where(Review.review_date >= filters.date_from)
    if filters.date_to is not None:
        base_query = base_query.where(Review.review_date <= filters.date_to)

    # Count before pagination
    count_result = await db.execute(select(func.count()).select_from(base_query.subquery()))
    total = count_result.scalar() or 0

    # Sort — allowlist key lookup is safe because Pydantic already validated sort_by (R1)
    sort_col = _SORT_COLS[filters.sort_by]
    order_fn = desc if filters.sort_order == "desc" else asc
    base_query = base_query.order_by(order_fn(sort_col))

    # Paginate
    offset = (filters.page - 1) * filters.page_size
    base_query = base_query.offset(offset).limit(filters.page_size)

    result = await db.execute(base_query)
    reviews = result.scalars().all()

    return ReviewPage(
        items=[ReviewOut.model_validate(r) for r in reviews],
        total=total,
        page=filters.page,
        page_size=filters.page_size,
        pages=ceil(total / filters.page_size) if total > 0 else 0,
    )
