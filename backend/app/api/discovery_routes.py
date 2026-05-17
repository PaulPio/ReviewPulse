from __future__ import annotations

import math
import os
from collections import Counter
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.api.books_routes import require_book
from app.api.schemas import CompareBookSummary, CompareRequest, CompareResponse, SearchHit, SearchRequest, SearchResponse, ThemeCount, WhatsNewItem
from app.dependencies import current_author, get_db_session
from app.llm.mock import MockLLMClient
from app.llm.openrouter import OpenRouterClient
from app.llm.protocol import LLMClient
from app.models import Author, Book, Review

router = APIRouter(tags=["discovery"])


def api_llm() -> LLMClient:
    if os.environ.get("USE_MOCK_LLM") == "1":
        return MockLLMClient()
    return OpenRouterClient()


@router.post("/search", response_model=SearchResponse)
def semantic_search(
    body: SearchRequest,
    author: Author = Depends(current_author),
    db: Session = Depends(get_db_session),
) -> SearchResponse:
    llm = api_llm()
    vec, _usage = llm.embed_texts([body.query])
    q = vec[0]
    dist_expr = Review.embedding.cosine_distance(q)
    stmt = (
        select(Review, Book)
        .join(Book, Review.book_id == Book.id)
        .where(Book.author_id == author.id, Review.embedding.isnot(None))
        .order_by(dist_expr)
        .limit(body.limit)
    )
    rows = db.execute(stmt).all()
    hits: list[SearchHit] = []
    for review, book in rows:
        emb = list(review.embedding)
        dot = sum(x * y for x, y in zip(emb, q, strict=False))
        na = math.sqrt(sum(x * x for x in emb))
        nb = math.sqrt(sum(x * x for x in q))
        sim = dot / (na * nb) if na and nb else 0.0
        snippet = review.body[:240] + ("…" if len(review.body) > 240 else "")
        hits.append(
            SearchHit(
                review_id=review.id,
                book_id=book.id,
                book_title=book.title,
                snippet=snippet,
                score=float(max(0.0, min(1.0, sim))),
            )
        )
    return SearchResponse(items=hits)


@router.post("/compare", response_model=CompareResponse)
def compare_books(
    body: CompareRequest,
    author: Author = Depends(current_author),
    db: Session = Depends(get_db_session),
) -> CompareResponse:
    summaries: list[CompareBookSummary] = []
    for bid in body.book_ids:
        b = require_book(db, author, bid)
        reviews = db.scalars(
            select(Review).options(joinedload(Review.analysis)).where(Review.book_id == b.id)
        ).unique().all()
        total = len(reviews)
        if total == 0:
            summaries.append(
                CompareBookSummary(
                    book_id=b.id,
                    title=b.title,
                    review_count=0,
                    sentiment_positive_pct=0.0,
                    sentiment_mixed_pct=0.0,
                    sentiment_negative_pct=0.0,
                    top_themes=[],
                    ai_flagged_pct=0.0,
                    reviews_per_week=0.0,
                )
            )
            continue
        analyzed = [r for r in reviews if r.analysis is not None]
        pos = sum(1 for r in analyzed if r.analysis and r.analysis.sentiment == "positive")
        neg = sum(1 for r in analyzed if r.analysis and r.analysis.sentiment == "negative")
        mix = sum(1 for r in analyzed if r.analysis and r.analysis.sentiment == "mixed")
        denom = max(len(analyzed), 1)
        themes: Counter[str] = Counter()
        ai_flags = sum(1 for r in analyzed if r.analysis and r.analysis.ai_generated)
        for r in analyzed:
            for t in r.analysis.themes or []:
                themes[str(t)] += 1
        dates = [r.review_date or r.created_at for r in reviews if (r.review_date or r.created_at)]
        rpw = 0.0
        if dates:
            aware: list[datetime] = []
            for d in dates:
                if d.tzinfo is None:
                    aware.append(d.replace(tzinfo=UTC))
                else:
                    aware.append(d.astimezone(UTC))
            span_days = max((max(aware) - min(aware)).days, 7)
            rpw = total / (span_days / 7.0)
        top = [ThemeCount(theme=k, count=c) for k, c in themes.most_common(5)]
        summaries.append(
            CompareBookSummary(
                book_id=b.id,
                title=b.title,
                review_count=total,
                sentiment_positive_pct=100.0 * pos / denom,
                sentiment_mixed_pct=100.0 * mix / denom,
                sentiment_negative_pct=100.0 * neg / denom,
                top_themes=top,
                ai_flagged_pct=100.0 * ai_flags / denom,
                reviews_per_week=rpw,
            )
        )
    return CompareResponse(books=summaries)


@router.get("/feed/whats-new", response_model=list[WhatsNewItem])
def whats_new(
    author: Author = Depends(current_author),
    db: Session = Depends(get_db_session),
    limit: int = 5,
) -> list[WhatsNewItem]:
    since = author.last_seen_at or (datetime.now(UTC) - timedelta(days=7))
    if since.tzinfo is None:
        since = since.replace(tzinfo=UTC)
    rows = db.scalars(
        select(Review)
        .join(Book, Review.book_id == Book.id)
        .options(joinedload(Review.analysis))
        .where(Book.author_id == author.id, Review.created_at > since)
    ).unique().all()

    def score(r: Review) -> float:
        if r.analysis is None:
            return 0.0
        s = 0.0
        if r.analysis.sentiment == "negative":
            s += 2.0
        if r.analysis.actionable:
            s += 1.0
        s += float(r.analysis.sentiment_confidence)
        if r.analysis.ai_generated:
            s -= 0.5
        return s

    enriched: list[tuple[Review, Book, float]] = []
    for r in rows:
        b = db.get(Book, r.book_id)
        if b is None:
            continue
        enriched.append((r, b, score(r)))
    enriched.sort(key=lambda t: t[2], reverse=True)
    out: list[WhatsNewItem] = []
    for r, b, sc in enriched[:limit]:
        summ = r.analysis.summary if r.analysis else r.body[:120]
        sent = r.analysis.sentiment if r.analysis else "unknown"
        act = bool(r.analysis and r.analysis.actionable)
        out.append(
            WhatsNewItem(
                review_id=r.id,
                book_title=b.title,
                summary=summ,
                sentiment=sent,
                actionable=act,
                score=float(sc),
            )
        )
    return out
