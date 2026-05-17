"""Semantic search endpoint using pgvector cosine similarity."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_author
from app.db.base import get_db
from app.models.author import Author
from app.models.book import Book
from app.models.review import Review
from app.schemas.review import SemanticSearchRequest, SemanticSearchResponse, SemanticSearchResult
from app.services.embedding import embed_text

router = APIRouter()


@router.post("", response_model=SemanticSearchResponse)
async def semantic_search(
    request: SemanticSearchRequest,
    current_author: Author = Depends(get_current_author),
    db: AsyncSession = Depends(get_db),
):
    # Generate embedding for the query
    try:
        query_embedding, _, _ = await embed_text(request.query)
    except Exception:
        raise HTTPException(status_code=503, detail="Embedding service unavailable")

    # Build query with cosine similarity
    embedding_literal = "[" + ",".join(str(x) for x in query_embedding) + "]"

    query = select(
        Review.id,
        Review.book_id,
        Review.body,
        Review.sentiment,
        Review.review_date,
        Review.rating,
        text(f"1 - (embedding <=> '{embedding_literal}'::vector) as score"),
    ).where(
        Review.author_id == current_author.id,
        Review.embedding.isnot(None),
    )

    if request.book_ids:
        query = query.where(Review.book_id.in_(request.book_ids))

    query = query.order_by(text(f"embedding <=> '{embedding_literal}'::vector")).limit(request.top_k)

    result = await db.execute(query)
    rows = result.all()

    # Get book titles
    book_ids = {row.book_id for row in rows}
    books_result = await db.execute(select(Book.id, Book.title).where(Book.id.in_(book_ids)))
    book_titles = dict(books_result.all())

    results = [
        SemanticSearchResult(
            review_id=row.id,
            book_id=row.book_id,
            book_title=book_titles.get(row.book_id, "Unknown"),
            snippet=row.body[:300],
            score=max(0, row.score) if row.score else 0,
            sentiment=row.sentiment,
            review_date=row.review_date,
            rating=row.rating,
        )
        for row in rows
    ]

    return SemanticSearchResponse(
        query=request.query,
        results=results,
        total_searched=len(rows),
    )
