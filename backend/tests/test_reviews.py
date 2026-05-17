"""
F3 — Review listing with filters, pagination, and sort tests.

Design under test
-----------------
GET /api/v1/books/{book_id}/reviews accepts:
  ?sentiment=positive|mixed|negative          (Literal — 422 on bad value)
  ?is_ai_generated=true|false
  ?is_actionable=true|false
  ?theme=<string>                             (membership check in ARRAY column)
  ?date_from=<iso-datetime>
  ?date_to=<iso-datetime>
  ?sort_by=review_date|rating|created_at|sentiment_confidence
  ?sort_order=asc|desc                        (Literal — 422 on bad value)
  ?page=<int ge=1>
  ?page_size=<int ge=1 le=100>                (422 on >100)

All filters are applied as SQL WHERE clauses.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.author import Author
from app.models.book import Book
from app.models.review import Review


# ------------------------------------------------------------------ helpers --

async def _make_book(db: AsyncSession, author: Author, title: str = "Test Book") -> Book:
    b = Book(id=uuid.uuid4(), author_id=author.id, title=title)
    db.add(b)
    await db.flush()
    return b


async def _make_review(
    db: AsyncSession,
    book: Book,
    author: Author,
    *,
    body: str = "A fine read.",
    rating: int | None = 4,
    review_date: datetime | None = None,
    sentiment: str | None = None,
    is_ai_generated: bool | None = None,
    is_actionable: bool | None = None,
    themes: list[str] | None = None,
    sentiment_confidence: float | None = None,
) -> Review:
    r = Review(
        book_id=book.id,
        author_id=author.id,
        external_id=uuid.uuid4().hex,
        body=body,
        rating=rating,
        review_date=review_date,
        sentiment=sentiment,
        sentiment_confidence=sentiment_confidence,
        is_ai_generated=is_ai_generated,
        is_actionable=is_actionable,
        themes=themes,
    )
    db.add(r)
    await db.flush()
    await db.refresh(r)
    return r


def _url(book: Book) -> str:
    return f"/api/v1/books/{book.id}/reviews"


# ----------------------------------------------- baseline / access control --


async def test_list_reviews_empty(
    client: AsyncClient, db: AsyncSession, author: Author
) -> None:
    book = await _make_book(db, author)
    resp = await client.get(_url(book))
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["pages"] == 0


async def test_list_reviews_404_for_wrong_author(
    client: AsyncClient, db: AsyncSession, another_author: Author
) -> None:
    """Reviews of another author's book return 404, not an empty list."""
    book = await _make_book(db, another_author)
    resp = await client.get(_url(book))
    assert resp.status_code == 404


async def test_list_reviews_404_for_nonexistent_book(
    client: AsyncClient, author: Author
) -> None:
    resp = await client.get(f"/api/v1/books/{uuid.uuid4()}/reviews")
    assert resp.status_code == 404


# ------------------------------------------------------- sentiment filter --


async def test_sentiment_filter_returns_only_matching(
    client: AsyncClient, db: AsyncSession, author: Author
) -> None:
    book = await _make_book(db, author)
    r_pos = await _make_review(db, book, author, sentiment="positive")
    r_neg = await _make_review(db, book, author, sentiment="negative")

    resp = await client.get(_url(book), params={"sentiment": "positive"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == str(r_pos.id)


async def test_sentiment_filter_excludes_unanalysed(
    client: AsyncClient, db: AsyncSession, author: Author
) -> None:
    """An unanalysed review (sentiment=None) must not appear when a sentiment filter is set."""
    book = await _make_book(db, author)
    await _make_review(db, book, author)  # no sentiment

    resp = await client.get(_url(book), params={"sentiment": "positive"})
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


async def test_no_analysis_filter_shows_unanalysed_reviews(
    client: AsyncClient, db: AsyncSession, author: Author
) -> None:
    """Without any analysis filter, unanalysed reviews should still appear."""
    book = await _make_book(db, author)
    await _make_review(db, book, author)  # no analysis

    resp = await client.get(_url(book))
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


# ----------------------------------------------------- is_ai_generated filter --


async def test_ai_generated_filter(
    client: AsyncClient, db: AsyncSession, author: Author
) -> None:
    book = await _make_book(db, author)
    r_ai = await _make_review(db, book, author, is_ai_generated=True)
    r_human = await _make_review(db, book, author, is_ai_generated=False)

    resp = await client.get(_url(book), params={"is_ai_generated": "true"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["is_ai_generated"] is True


# ---------------------------------------------------- is_actionable filter --


async def test_actionable_filter(
    client: AsyncClient, db: AsyncSession, author: Author
) -> None:
    book = await _make_book(db, author)
    r_act = await _make_review(db, book, author, is_actionable=True)
    r_not = await _make_review(db, book, author, is_actionable=False)

    resp = await client.get(_url(book), params={"is_actionable": "true"})
    assert resp.status_code == 200
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["id"] == str(r_act.id)


# --------------------------------------------------------- theme filter --


async def test_theme_filter(
    client: AsyncClient, db: AsyncSession, author: Author
) -> None:
    book = await _make_book(db, author)
    r_plot = await _make_review(db, book, author, themes=["plot", "pacing"])
    r_char = await _make_review(db, book, author, themes=["characters"])

    resp = await client.get(_url(book), params={"theme": "plot"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == str(r_plot.id)


async def test_theme_filter_no_match(
    client: AsyncClient, db: AsyncSession, author: Author
) -> None:
    book = await _make_book(db, author)
    await _make_review(db, book, author, themes=["characters"])

    resp = await client.get(_url(book), params={"theme": "nonexistent_theme"})
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


# ------------------------------------------------------ date range filter --


async def test_date_from_filter(
    client: AsyncClient, db: AsyncSession, author: Author
) -> None:
    now = datetime.now(UTC)
    book = await _make_book(db, author)
    r_old = await _make_review(db, book, author, review_date=now - timedelta(days=30))
    r_new = await _make_review(db, book, author, review_date=now - timedelta(days=1))

    cutoff = (now - timedelta(days=7)).isoformat()
    resp = await client.get(_url(book), params={"date_from": cutoff})
    assert resp.status_code == 200
    ids = {item["id"] for item in resp.json()["items"]}
    assert str(r_new.id) in ids
    assert str(r_old.id) not in ids


async def test_date_to_filter(
    client: AsyncClient, db: AsyncSession, author: Author
) -> None:
    now = datetime.now(UTC)
    book = await _make_book(db, author)
    r_old = await _make_review(db, book, author, review_date=now - timedelta(days=30))
    r_new = await _make_review(db, book, author, review_date=now - timedelta(days=1))

    cutoff = (now - timedelta(days=7)).isoformat()
    resp = await client.get(_url(book), params={"date_to": cutoff})
    assert resp.status_code == 200
    ids = {item["id"] for item in resp.json()["items"]}
    assert str(r_old.id) in ids
    assert str(r_new.id) not in ids


# ----------------------------------------------------------- sort order --


async def test_sort_by_rating(
    client: AsyncClient, db: AsyncSession, author: Author
) -> None:
    book = await _make_book(db, author)
    await _make_review(db, book, author, rating=2)
    await _make_review(db, book, author, rating=5)
    await _make_review(db, book, author, rating=4)

    resp = await client.get(_url(book), params={"sort_by": "rating"})
    assert resp.status_code == 200
    ratings = [item["rating"] for item in resp.json()["items"]]
    assert ratings == sorted(ratings, reverse=True)


async def test_sort_invalid_value_returns_422(
    client: AsyncClient, db: AsyncSession, author: Author
) -> None:
    """Unrecognised sort_by value must be rejected at input validation (422)."""
    book = await _make_book(db, author)
    resp = await client.get(_url(book), params={"sort_by": "popularity"})
    assert resp.status_code == 422


async def test_sort_order_invalid_returns_422(
    client: AsyncClient, db: AsyncSession, author: Author
) -> None:
    """Unrecognised sort_order value must be rejected at input validation (422)."""
    book = await _make_book(db, author)
    resp = await client.get(_url(book), params={"sort_order": "random"})
    assert resp.status_code == 422


# ----------------------------------------------------------- pagination --


async def test_pagination_total_and_pages(
    client: AsyncClient, db: AsyncSession, author: Author
) -> None:
    book = await _make_book(db, author)
    for _ in range(25):
        await _make_review(db, book, author)

    resp = await client.get(_url(book), params={"page": 1, "page_size": 10})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 25
    assert data["pages"] == 3
    assert len(data["items"]) == 10


async def test_pagination_page_2(
    client: AsyncClient, db: AsyncSession, author: Author
) -> None:
    book = await _make_book(db, author)
    for _ in range(15):
        await _make_review(db, book, author)

    p1 = (await client.get(_url(book), params={"page": 1, "page_size": 10})).json()
    p2 = (await client.get(_url(book), params={"page": 2, "page_size": 10})).json()

    ids_p1 = {i["id"] for i in p1["items"]}
    ids_p2 = {i["id"] for i in p2["items"]}
    assert ids_p1.isdisjoint(ids_p2)
    assert len(p2["items"]) == 5


async def test_pagination_beyond_last_page_returns_empty(
    client: AsyncClient, db: AsyncSession, author: Author
) -> None:
    book = await _make_book(db, author)
    await _make_review(db, book, author)

    resp = await client.get(_url(book), params={"page": 999, "page_size": 10})
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 1


async def test_page_size_capped_at_100(
    client: AsyncClient, db: AsyncSession, author: Author
) -> None:
    book = await _make_book(db, author)
    resp = await client.get(_url(book), params={"page_size": 999})
    assert resp.status_code == 422


# ------------------------------------------------------- combined filters --


async def test_combined_sentiment_and_actionable(
    client: AsyncClient, db: AsyncSession, author: Author
) -> None:
    """Multiple filters are ANDed — only rows matching all conditions appear."""
    book = await _make_book(db, author)
    r_match = await _make_review(db, book, author, sentiment="negative", is_actionable=True)
    r_no_match = await _make_review(db, book, author, sentiment="negative", is_actionable=False)

    resp = await client.get(
        _url(book),
        params={"sentiment": "negative", "is_actionable": "true"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == str(r_match.id)
