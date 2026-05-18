"""
Book CRUD and catalog endpoints.

GET  /books           — list all books with stats (catalog view, F6 input)
POST /books           — add a book to the catalog
GET  /books/{id}      — per-book deep-dive with full stats
DELETE /books/{id}    — remove a book and all its reviews (CASCADE)

The BookWithStats response includes aggregated review metrics computed
with a single SQL query per book, so the catalog view loads in one
round-trip per book. For large catalogs (>50 books), this should be
replaced with a subquery approach to avoid N+1.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_author
from app.db.base import get_db
from app.models.author import Author
from app.models.book import Book
from app.models.ingestion_job import IngestionJob
from app.models.llm_usage import LLMUsage
from app.models.review import Review
from app.schemas.book import BookCreate, BookOut, BookWithStats
from app.schemas.job import JobOut

router = APIRouter()


async def _get_book_stats(db: AsyncSession, book_id) -> dict:
    """Single-query aggregation of review stats for a book."""
    review_stats = await db.execute(
        select(
            func.count(Review.id).label("total"),
            func.count(Review.id).filter(Review.sentiment == "positive").label("pos"),
            func.count(Review.id).filter(Review.sentiment == "mixed").label("mix"),
            func.count(Review.id).filter(Review.sentiment == "negative").label("neg"),
            func.count(Review.id).filter(Review.is_ai_generated == True).label("ai_flagged"),  # noqa: E712
            func.count(Review.id).filter(Review.is_actionable == True).label("actionable"),  # noqa: E712
            func.avg(Review.rating).label("avg_rating"),
            func.max(Review.review_date).label("last_review_at"),
        ).where(Review.book_id == book_id)
    )
    row = review_stats.one()

    cost_result = await db.execute(
        select(func.sum(LLMUsage.cost_usd_micros)).where(LLMUsage.book_id == book_id)
    )
    total_cost_micros = cost_result.scalar() or 0

    return {
        "total_reviews": row.total or 0,
        "avg_rating": round(row.avg_rating, 2) if row.avg_rating else None,
        "sentiment_positive": row.pos or 0,
        "sentiment_mixed": row.mix or 0,
        "sentiment_negative": row.neg or 0,
        "ai_flagged_count": row.ai_flagged or 0,
        "actionable_count": row.actionable or 0,
        "last_review_at": row.last_review_at,
        "total_cost_usd": round(total_cost_micros / 1_000_000, 6),
    }


@router.post("", response_model=BookOut, status_code=status.HTTP_201_CREATED)
async def create_book(
    data: BookCreate,
    current_author: Author = Depends(get_current_author),
    db: AsyncSession = Depends(get_db),
):
    book = Book(
        id=uuid.uuid4(),
        author_id=current_author.id,
        title=data.title,
        isbn=data.isbn,
        asin=data.asin,
        amazon_url=data.amazon_url,
        cover_url=data.cover_url,
        description=data.description,
        published_at=data.published_at,
    )
    db.add(book)
    await db.flush()
    await db.refresh(book)
    return BookOut.model_validate(book)


@router.get("", response_model=list[BookWithStats])
async def list_books(
    current_author: Author = Depends(get_current_author),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Book).where(Book.author_id == current_author.id).order_by(Book.created_at.desc())
    )
    books = result.scalars().all()

    out = []
    for book in books:
        stats = await _get_book_stats(db, book.id)
        out.append(BookWithStats(**BookOut.model_validate(book).model_dump(), **stats))
    return out


@router.get("/{book_id}", response_model=BookWithStats)
async def get_book(
    book_id: uuid.UUID,
    current_author: Author = Depends(get_current_author),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Book).where(Book.id == book_id, Book.author_id == current_author.id)
    )
    book = result.scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    stats = await _get_book_stats(db, book.id)
    return BookWithStats(**BookOut.model_validate(book).model_dump(), **stats)


@router.post("/{book_id}/ingest", response_model=JobOut, status_code=status.HTTP_202_ACCEPTED)
async def trigger_ingestion(
    book_id: uuid.UUID,
    current_author: Author = Depends(get_current_author),
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger an async ingestion job for a book.

    Returns 202 Accepted immediately — the HTTP connection is not held open.
    Clients poll GET /api/v1/jobs/{id} until status is completed | failed | partial.
    This follows the fire-and-forget pattern described in RFC 9110 §15.3.3.
    """
    result = await db.execute(
        select(Book).where(Book.id == book_id, Book.author_id == current_author.id)
    )
    book = result.scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    # 409 if a job is already active for this book
    active_result = await db.execute(
        select(IngestionJob).where(
            IngestionJob.book_id == book_id,
            IngestionJob.author_id == current_author.id,
            IngestionJob.status.in_(["queued", "running"]),
        )
    )
    if active_result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="An ingestion job is already active for this book")

    job = IngestionJob(
        book_id=book_id,
        author_id=current_author.id,
        status="queued",
    )
    db.add(job)
    await db.flush()
    await db.refresh(job)

    # Deferred import so API startup does not load Celery/broker (fine on Render without Redis).
    from app.tasks.ingestion import run_ingestion_job

    task = run_ingestion_job.delay(str(job.id))
    job.celery_task_id = task.id
    await db.flush()

    return JobOut.model_validate(job)


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_book(
    book_id: uuid.UUID,
    current_author: Author = Depends(get_current_author),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Book).where(Book.id == book_id, Book.author_id == current_author.id)
    )
    book = result.scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    await db.delete(book)
