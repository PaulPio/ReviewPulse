from __future__ import annotations

import csv
import io
import uuid
from collections import Counter
from datetime import UTC, date, datetime, timedelta
from statistics import mean

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.api.schemas import (
    BookCatalogOut,
    BookCreate,
    BookOut,
    DigestPreview,
    JobOut,
    ReviewAnalysisOut,
    ReviewListResponse,
    ReviewOut,
    ThemeCount,
    TrendPoint,
    TrendsResponse,
)
from app.dependencies import current_author, get_db_session
from app.models import Author, Book, Job, JobKind, JobStatus, Review, ReviewAnalysis
from app.tasks import run_ingest_job

router = APIRouter(tags=["books"])


def require_book(db: Session, author: Author, book_id: uuid.UUID) -> Book:
    b = db.scalar(select(Book).where(Book.id == book_id, Book.author_id == author.id))
    if b is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    return b


@router.get("/books", response_model=list[BookCatalogOut])
def list_books(
    author: Author = Depends(current_author),
    db: Session = Depends(get_db_session),
) -> list[BookCatalogOut]:
    rows = db.scalars(
        select(Book).where(Book.author_id == author.id).order_by(Book.created_at.desc())
    ).all()
    out: list[BookCatalogOut] = []
    for b in rows:
        revs = (
            db.scalar(select(func.count()).select_from(Review).where(Review.book_id == b.id)) or 0
        )
        analyzed = (
            db.scalar(
                select(func.count())
                .select_from(Review)
                .join(ReviewAnalysis, ReviewAnalysis.review_id == Review.id)
                .where(Review.book_id == b.id)
            )
            or 0
        )
        neg = (
            db.scalar(
                select(func.count())
                .select_from(Review)
                .join(ReviewAnalysis, ReviewAnalysis.review_id == Review.id)
                .where(Review.book_id == b.id, ReviewAnalysis.sentiment == "negative")
            )
            or 0
        )
        pct = (100.0 * neg / analyzed) if analyzed else None
        out.append(
            BookCatalogOut(
                id=b.id,
                title=b.title,
                isbn=b.isbn,
                asin=b.asin,
                catalog_url=b.catalog_url,
                created_at=b.created_at,
                review_count=int(revs),
                analyzed_count=int(analyzed),
                pct_negative=pct,
            )
        )
    return out


@router.post("/books", response_model=BookOut)
def create_book(
    body: BookCreate,
    author: Author = Depends(current_author),
    db: Session = Depends(get_db_session),
) -> Book:
    b = Book(
        author_id=author.id,
        title=body.title,
        isbn=body.isbn,
        asin=(body.asin or "").upper() or None,
        catalog_url=body.catalog_url,
    )
    db.add(b)
    db.commit()
    db.refresh(b)
    return b


@router.post("/books/{book_id}/ingest", response_model=JobOut)
def ingest_book(
    book_id: uuid.UUID,
    author: Author = Depends(current_author),
    db: Session = Depends(get_db_session),
    idempotency_key: str | None = Header(
        default=None,
        convert_underscores=False,
        alias="Idempotency-Key",
    ),
) -> Job:
    require_book(db, author, book_id)
    key = (idempotency_key or "").strip() or None
    if key:
        existing = db.scalar(
            select(Job).where(
                Job.author_id == author.id,
                Job.book_id == book_id,
                Job.kind == JobKind.ingest_book,
                Job.idempotency_key == key,
            )
        )
        if existing is not None:
            return existing

    job = Job(
        author_id=author.id,
        book_id=book_id,
        kind=JobKind.ingest_book,
        status=JobStatus.queued,
        job_data={},
        idempotency_key=key,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    run_ingest_job.delay(str(job.id))
    return job


def _review_to_out(r: Review) -> ReviewOut:
    analysis = (
        ReviewAnalysisOut.model_validate(r.analysis) if r.analysis is not None else None
    )
    return ReviewOut(
        id=r.id,
        book_id=r.book_id,
        body=r.body,
        rating=r.rating,
        review_date=r.review_date,
        created_at=r.created_at,
        analysis=analysis,
    )


@router.get("/books/{book_id}/reviews", response_model=ReviewListResponse)
def list_reviews(
    book_id: uuid.UUID,
    author: Author = Depends(current_author),
    db: Session = Depends(get_db_session),
    sentiment: str | None = None,
    ai_flagged: bool | None = None,
    actionable: bool | None = None,
    theme: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort: str = Query("recent", pattern="^(recent|rating)$"),
) -> ReviewListResponse:
    require_book(db, author, book_id)
    rows = db.scalars(
        select(Review)
        .options(joinedload(Review.analysis))
        .where(Review.book_id == book_id)
        .order_by(Review.created_at.desc())
    ).unique().all()
    filtered: list[Review] = []
    for r in rows:
        ts = r.review_date or r.created_at
        if date_from and ts and ts < date_from:
            continue
        if date_to and ts and ts > date_to:
            continue
        if sentiment and (r.analysis is None or r.analysis.sentiment != sentiment):
            continue
        if ai_flagged is not None and (
            r.analysis is None or r.analysis.ai_generated != ai_flagged
        ):
            continue
        if actionable is not None and (
            r.analysis is None or r.analysis.actionable != actionable
        ):
            continue
        if theme and (r.analysis is None or theme not in (r.analysis.themes or [])):
            continue
        filtered.append(r)
    total = len(filtered)
    if sort == "rating":
        filtered.sort(key=lambda r: (r.rating is None, -(r.rating or 0)))
    start = (page - 1) * page_size
    page_rows = filtered[start : start + page_size]
    return ReviewListResponse(
        items=[_review_to_out(r) for r in page_rows],
        total=total,
        page=page,
        page_size=page_size,
    )


def _sentiment_score(label: str) -> float:
    if label == "positive":
        return 1.0
    if label == "negative":
        return -1.0
    return 0.0


@router.get("/books/{book_id}/trends", response_model=TrendsResponse)
def book_trends(
    book_id: uuid.UUID,
    author: Author = Depends(current_author),
    db: Session = Depends(get_db_session),
) -> TrendsResponse:
    book = require_book(db, author, book_id)
    rows = db.scalars(
        select(Review)
        .options(joinedload(Review.analysis))
        .where(Review.book_id == book_id)
        .order_by(Review.created_at.asc())
    ).unique().all()
    by_week: dict[date, list[float]] = {}
    theme_counter: Counter[str] = Counter()
    for r in rows:
        if not r.analysis:
            continue
        ts = r.review_date or r.created_at
        if isinstance(ts, datetime):
            d = ts.astimezone(UTC).date()
        else:
            d = date.today()
        week_start = d - timedelta(days=d.weekday())
        sc = _sentiment_score(r.analysis.sentiment)
        by_week.setdefault(week_start, []).append(sc)
        for t in r.analysis.themes or []:
            theme_counter[str(t)] += 1
    series = [
        TrendPoint(
            period_start=k,
            avg_sentiment_score=mean(v) if v else 0.0,
            review_count=len(v),
        )
        for k, v in sorted(by_week.items(), key=lambda kv: kv[0])
    ]
    themes = [ThemeCount(theme=k, count=v) for k, v in theme_counter.most_common(10)]
    return TrendsResponse(book_id=book.id, granularity="week", series=series, theme_counts=themes)


@router.get("/books/{book_id}/digest", response_model=DigestPreview)
def book_digest(
    book_id: uuid.UUID,
    author: Author = Depends(current_author),
    db: Session = Depends(get_db_session),
) -> DigestPreview:
    book = require_book(db, author, book_id)
    analyses = db.scalars(
        select(ReviewAnalysis)
        .join(Review, Review.id == ReviewAnalysis.review_id)
        .where(Review.book_id == book_id)
        .order_by(ReviewAnalysis.created_at.desc())
        .limit(20)
    ).all()
    if not analyses:
        return DigestPreview(
            html=f"<p>No analyzed reviews yet for <strong>{book.title}</strong>.</p>"
        )
    neg = sum(1 for a in analyses if a.sentiment == "negative")
    pos = sum(1 for a in analyses if a.sentiment == "positive")
    lines = [
        f"<h1>Weekly digest — {book.title}</h1>",
        f"<p><strong>Snapshot:</strong> {pos} positive, {neg} negative/mixed signals in recent batch.</p>",
        "<ul>",
    ]
    for a in analyses[:5]:
        lines.append(f"<li><em>{a.sentiment}</em> — {a.summary}</li>")
    lines.append("</ul>")
    lines.append("<p><small>Preview only — no email sent.</small></p>")
    return DigestPreview(html="".join(lines))


@router.get("/books/{book_id}/export.csv")
def export_themed_quotes(
    book_id: uuid.UUID,
    author: Author = Depends(current_author),
    db: Session = Depends(get_db_session),
    theme: str | None = None,
) -> Response:
    """P1: curated export for editors (CSV of themed quotes)."""
    book = require_book(db, author, book_id)
    rows = db.scalars(
        select(Review)
        .options(joinedload(Review.analysis))
        .where(Review.book_id == book_id)
        .order_by(Review.created_at.desc())
    ).unique().all()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["review_id", "rating", "themes", "snippet", "sentiment"])
    for r in rows:
        if not r.analysis:
            continue
        th = ",".join(r.analysis.themes or [])
        if theme and theme not in (r.analysis.themes or []):
            continue
        w.writerow([str(r.id), r.rating or "", th, r.body[:500], r.analysis.sentiment])
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{book.title[:40]}-quotes.csv"'},
    )
