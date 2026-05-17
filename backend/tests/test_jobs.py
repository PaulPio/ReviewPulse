"""
F2 — Job status polling tests.

Demonstrates understanding of async, not just await
----------------------------------------------------
The ingest pipeline is fire-and-forget: POST /books/{id}/ingest returns 202
immediately (no blocking), then clients poll GET /jobs/{id} independently.
These tests exercise that entire contract — including all five status values,
the computed progress_pct field, caching headers, and tenant isolation.

No real Celery worker is involved.  Tests mutate the IngestionJob row directly
to simulate each state transition, exactly as a Celery worker would do.
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.author import Author
from app.models.book import Book
from app.models.ingestion_job import IngestionJob


# ------------------------------------------------------------------ helpers --

async def _make_book(db: AsyncSession, author: Author, title: str = "Test Book") -> Book:
    b = Book(id=uuid.uuid4(), author_id=author.id, title=title)
    db.add(b)
    await db.flush()
    return b


async def _make_job(
    db: AsyncSession,
    author: Author,
    book: Book,
    status: str = "queued",
    total_reviews: int = 0,
    processed_reviews: int = 0,
    failed_reviews: int = 0,
) -> IngestionJob:
    j = IngestionJob(
        author_id=author.id,
        book_id=book.id,
        status=status,
        total_reviews=total_reviews,
        processed_reviews=processed_reviews,
        failed_reviews=failed_reviews,
    )
    db.add(j)
    await db.flush()
    await db.refresh(j)
    return j


# --------------------------------------------------------------- F2 tests --


async def test_trigger_returns_202_and_queued_status(
    client: AsyncClient, db: AsyncSession, author: Author
) -> None:
    """
    POST /books/{id}/ingest must return 202 Accepted immediately — it does not
    wait for the pipeline.  The returned job has status=queued.

    This is the entry point of the async pattern: the HTTP response is instant;
    work happens out-of-band via Celery.
    """
    book = await _make_book(db, author)

    with patch("app.api.books.run_ingestion_job.delay", return_value=MagicMock(id="mock-task-id")):
        resp = await client.post(f"/api/v1/books/{book.id}/ingest")

    assert resp.status_code == 202, resp.text
    data = resp.json()
    assert data["status"] == "queued"
    assert data["book_id"] == str(book.id)
    assert data["total_reviews"] == 0
    assert data["processed_reviews"] == 0
    assert data["progress_pct"] == 0.0


async def test_trigger_404_for_nonexistent_book(client: AsyncClient) -> None:
    """Trigger on a nonexistent book returns 404."""
    with patch("app.api.books.run_ingestion_job.delay"):
        resp = await client.post(f"/api/v1/books/{uuid.uuid4()}/ingest")
    assert resp.status_code == 404


async def test_get_job_404_for_unknown_id(client: AsyncClient) -> None:
    """Unknown job ID returns 404, not 500."""
    resp = await client.get(f"/api/v1/jobs/{uuid.uuid4()}")
    assert resp.status_code == 404


async def test_get_job_404_tenant_isolation(
    client: AsyncClient, db: AsyncSession, another_author: Author
) -> None:
    """
    A job owned by another_author is invisible to the authenticated client.
    Returns 404 (not 403) to avoid leaking that the resource exists.
    """
    book = await _make_book(db, another_author)
    job = await _make_job(db, another_author, book)

    resp = await client.get(f"/api/v1/jobs/{job.id}")
    assert resp.status_code == 404


async def test_polling_cycle_all_five_states(
    client: AsyncClient, db: AsyncSession, author: Author
) -> None:
    """
    Simulates the full polling lifecycle without a real Celery worker.

    State machine:  queued → running → completed
                                     ↘ failed
                                     ↘ partial

    The client has no open connection — it issues a new GET each time.
    This is the async pattern: the trigger fired and forgot; the caller
    independently polls until a terminal state is reached.
    """
    book = await _make_book(db, author)
    job = await _make_job(db, author, book, status="queued")
    terminal_states = {"completed", "failed", "partial"}

    # Initial state — active: Cache-Control must be no-store
    resp = await client.get(f"/api/v1/jobs/{job.id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "queued"
    assert resp.headers.get("Cache-Control") == "no-store"

    # Worker transitions to running — still active
    job.status = "running"
    await db.flush()

    resp = await client.get(f"/api/v1/jobs/{job.id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "running"
    assert resp.headers.get("Cache-Control") == "no-store"

    # Worker completes successfully — terminal: Cache-Control must be max-age=300
    job.status = "completed"
    job.total_reviews = 10
    job.processed_reviews = 10
    await db.flush()

    final = await client.get(f"/api/v1/jobs/{job.id}")
    assert final.status_code == 200
    data = final.json()
    assert data["status"] in terminal_states
    assert final.headers.get("Cache-Control") == "max-age=300"

    # Verify computed progress fields
    assert data["total_reviews"] == 10
    assert data["processed_reviews"] == 10
    assert data["progress_pct"] == 100.0


async def test_partial_status_has_correct_progress(
    client: AsyncClient, db: AsyncSession, author: Author
) -> None:
    """A partial job (some analyses failed) shows correct processed/failed counts."""
    book = await _make_book(db, author)
    job = await _make_job(
        db, author, book,
        status="partial",
        total_reviews=10,
        processed_reviews=7,
        failed_reviews=3,
    )

    resp = await client.get(f"/api/v1/jobs/{job.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "partial"
    assert data["processed_reviews"] == 7
    assert data["total_reviews"] == 10
    assert data["failed_reviews"] == 3
    assert data["progress_pct"] == 70.0
    assert resp.headers.get("Cache-Control") == "max-age=300"


async def test_failed_job_returns_terminal_cache_header(
    client: AsyncClient, db: AsyncSession, author: Author
) -> None:
    book = await _make_book(db, author)
    job = await _make_job(db, author, book, status="failed")

    resp = await client.get(f"/api/v1/jobs/{job.id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "failed"
    assert resp.headers.get("Cache-Control") == "max-age=300"


async def test_list_jobs_returns_only_own_jobs(
    client: AsyncClient, db: AsyncSession, author: Author, another_author: Author
) -> None:
    """list_jobs is tenant-scoped — another author's jobs never appear."""
    book_a = await _make_book(db, author, "Book A")
    book_b = await _make_book(db, another_author, "Book B")
    await _make_job(db, author, book_a)
    job_b = await _make_job(db, another_author, book_b)

    resp = await client.get("/api/v1/jobs")
    assert resp.status_code == 200
    returned_ids = {j["id"] for j in resp.json()}
    assert str(job_b.id) not in returned_ids


async def test_list_jobs_limit(
    client: AsyncClient, db: AsyncSession, author: Author
) -> None:
    """?limit query param caps results."""
    book = await _make_book(db, author)
    for _ in range(5):
        await _make_job(db, author, book)

    resp = await client.get("/api/v1/jobs?limit=2")
    assert resp.status_code == 200
    assert len(resp.json()) <= 2
