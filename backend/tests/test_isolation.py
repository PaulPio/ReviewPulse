"""
Multi-tenant isolation tests (N6, F12).

Two types of tests:
1. Structural — verify author_id dependency is present in every route handler
   (fast, no DB required)
2. Integration — make real HTTP requests with two different author JWTs and
   confirm cross-tenant access is rejected (requires test DB)

The isolation guarantee:
  - Every query in the API layer filters on `author_id = current_author.id`
  - `get_current_author` is the single entry point for authenticated requests
  - Reviews have a denormalised `author_id` column so a single-table filter
    blocks cross-tenant access without a JOIN

These tests are the N6 tests that "demonstrate multi-tenant isolation
can't be bypassed" as required by the spec.
"""

from __future__ import annotations

import inspect
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book import Book
from app.models.ingestion_job import IngestionJob
from app.models.review import Review


# ------------------------------------------------------------------ #
# Structural tests — no I/O, run fast
# ------------------------------------------------------------------ #

class TestIsolationStructure:
    """Verify `current_author` dependency is present in every protected route."""

    def test_books_list_requires_author(self):
        from app.api.books import list_books
        assert "current_author" in inspect.signature(list_books).parameters

    def test_books_get_requires_author(self):
        from app.api.books import get_book
        assert "current_author" in inspect.signature(get_book).parameters

    def test_books_delete_requires_author(self):
        from app.api.books import delete_book
        assert "current_author" in inspect.signature(delete_book).parameters

    def test_reviews_list_requires_author(self):
        from app.api.reviews import list_reviews
        assert "current_author" in inspect.signature(list_reviews).parameters

    def test_jobs_get_requires_author(self):
        from app.api.jobs import get_job
        assert "current_author" in inspect.signature(get_job).parameters

    def test_jobs_list_requires_author(self):
        from app.api.jobs import list_jobs
        assert "current_author" in inspect.signature(list_jobs).parameters

    def test_search_requires_author(self):
        from app.api.search import semantic_search
        assert "current_author" in inspect.signature(semantic_search).parameters

    def test_analytics_trends_requires_author(self):
        from app.api.analytics import get_trends
        assert "current_author" in inspect.signature(get_trends).parameters

    def test_metrics_requires_author(self):
        from app.api.metrics import get_metrics
        assert "current_author" in inspect.signature(get_metrics).parameters


# ------------------------------------------------------------------ #
# Runtime isolation tests — require test DB
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_book_cross_tenant_read_blocked(
    client: AsyncClient,
    client_other: AsyncClient,
    db: AsyncSession,
    author,
    another_author,
):
    """Author B cannot read Author A's book by its UUID."""
    book_a = Book(id=uuid.uuid4(), author_id=author.id, title="Author A's Private Book")
    db.add(book_a)
    await db.flush()

    # Author A can read their book
    resp_a = await client.get(f"/api/v1/books/{book_a.id}")
    assert resp_a.status_code == 200
    assert resp_a.json()["id"] == str(book_a.id)

    # Author B is blocked — 404 (we don't leak the existence of the resource)
    resp_b = await client_other.get(f"/api/v1/books/{book_a.id}")
    assert resp_b.status_code == 404


@pytest.mark.asyncio
async def test_book_list_scoped_to_author(
    client: AsyncClient,
    client_other: AsyncClient,
    db: AsyncSession,
    author,
    another_author,
):
    """Each author sees only their own books in the catalog list."""
    book_a = Book(id=uuid.uuid4(), author_id=author.id, title="Alpha's Thriller")
    book_b = Book(id=uuid.uuid4(), author_id=another_author.id, title="Beta's Romance")
    db.add(book_a)
    db.add(book_b)
    await db.flush()

    ids_for_a = [b["id"] for b in (await client.get("/api/v1/books")).json()]
    ids_for_b = [b["id"] for b in (await client_other.get("/api/v1/books")).json()]

    assert str(book_a.id) in ids_for_a
    assert str(book_b.id) not in ids_for_a

    assert str(book_b.id) in ids_for_b
    assert str(book_a.id) not in ids_for_b


@pytest.mark.asyncio
async def test_job_cross_tenant_read_blocked(
    client: AsyncClient,
    client_other: AsyncClient,
    db: AsyncSession,
    author,
    another_author,
):
    """Author B cannot poll Author A's ingestion job by its UUID."""
    book_a = Book(id=uuid.uuid4(), author_id=author.id, title="Book A")
    db.add(book_a)
    await db.flush()

    job = IngestionJob(
        id=uuid.uuid4(),
        book_id=book_a.id,
        author_id=author.id,
        status="completed",
    )
    db.add(job)
    await db.flush()

    resp_a = await client.get(f"/api/v1/jobs/{job.id}")
    assert resp_a.status_code == 200

    resp_b = await client_other.get(f"/api/v1/jobs/{job.id}")
    assert resp_b.status_code == 404


@pytest.mark.asyncio
async def test_unauthenticated_request_blocked(db: AsyncSession):
    """Requests without a JWT Authorization header are rejected with 403."""
    from httpx import AsyncClient, ASGITransport
    from app.db.base import get_db
    from app.main import app

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as anon:
            response = await anon.get("/api/v1/books")
            assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()
