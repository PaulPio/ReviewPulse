"""Review listing with filters and pagination."""

from __future__ import annotations

import uuid
from math import ceil

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_author
from app.db.base import get_db
from app.models.author import Author
from app.models.review import Review
from app.schemas.review import ReviewOut, ReviewFilter, ReviewPage

router = APIRouter()


@router.get("/books/{book_id}/reviews", response_model=ReviewPage)
async def list_reviews(
    book_id: uuid.UUID,
    sentiment: str | None = None,
    is_ai_generated: bool | None = None,
    is_actionable: bool | None = None,
    theme: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    sort_by: str = "review_date",
    sort_order: str = "desc",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_author: Author = Depends(get_current_author),
    db: AsyncSession = Depends(get_db),
):
    base_query = select(Review).where(
        Review.book_id == book_id,
        Review.author_id == current_author.id,
    )

    # Apply filters
    if sentiment:
        base_query = base_query.where(Review.sentiment == sentiment)
    if is_ai_generated is not None:
        base_query = base_query.where(Review.is_ai_generated == is_ai_generated)
    if is_actionable is not None:
        base_query = base_query.where(Review.is_actionable == is_actionable)
    if theme:
        base_query = base_query.where(Review.themes.any(theme))
    if date_from:
        base_query = base_query.where(Review.review_date >= date_from)
    if date_to:
        base_query = base_query.where(Review.review_date <= date_to)

    # Count total
    count_result = await db.execute(select(func.count()).select_from(base_query.subquery()))
    total = count_result.scalar() or 0

    # Sort
    sort_col = getattr(Review, sort_by, Review.review_date)
    order_fn = desc if sort_order == "desc" else asc
    base_query = base_query.order_by(order_fn(sort_col))

    # Paginate
    offset = (page - 1) * page_size
    base_query = base_query.offset(offset).limit(page_size)

    result = await db.execute(base_query)
    reviews = result.scalars().all()

    return ReviewPage(
        items=[ReviewOut.model_validate(r) for r in reviews],
        total=total,
        page=page,
        page_size=page_size,
        pages=ceil(total / page_size) if total > 0 else 0,
    )
