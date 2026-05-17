from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.schemas import SpendSummary
from app.dependencies import current_author, get_db_session
from app.models import Author, Book, Review, ReviewAnalysis

router = APIRouter(tags=["metrics"])


@router.get("/metrics/summary", response_model=SpendSummary)
def spend_summary(
    author: Author = Depends(current_author),
    db: Session = Depends(get_db_session),
) -> SpendSummary:
    total_cost, pt, ct = db.execute(
        select(
            func.coalesce(func.sum(ReviewAnalysis.estimated_cost_usd), 0.0),
            func.coalesce(func.sum(ReviewAnalysis.prompt_tokens), 0),
            func.coalesce(func.sum(ReviewAnalysis.completion_tokens), 0),
        )
        .select_from(ReviewAnalysis)
        .join(Review, ReviewAnalysis.review_id == Review.id)
        .join(Book, Review.book_id == Book.id)
        .where(Book.author_id == author.id)
    ).one()

    by_book_rows = db.execute(
        select(Book.id, Book.title, func.coalesce(func.sum(ReviewAnalysis.estimated_cost_usd), 0.0))
        .join(Review, Review.book_id == Book.id)
        .join(ReviewAnalysis, ReviewAnalysis.review_id == Review.id)
        .where(Book.author_id == author.id)
        .group_by(Book.id, Book.title)
    ).all()
    by_book: dict[str, float] = {str(title): float(cost) for _id, title, cost in by_book_rows}
    return SpendSummary(
        total_estimated_cost_usd=float(total_cost or 0.0),
        total_prompt_tokens=int(pt or 0),
        total_completion_tokens=int(ct or 0),
        by_book=by_book,
    )


@router.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
