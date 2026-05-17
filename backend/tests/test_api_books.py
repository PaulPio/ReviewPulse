"""
API integration tests for book CRUD endpoints.
All tests use the test DB session via the `client` fixture.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book import Book


@pytest.mark.asyncio
async def test_create_book(client: AsyncClient):
    resp = await client.post(
        "/api/v1/books",
        json={"title": "My New Novel", "isbn": "9780000000001"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "My New Novel"
    assert data["isbn"] == "9780000000001"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_books_empty(client: AsyncClient):
    resp = await client.get("/api/v1/books")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_get_book(client: AsyncClient, book: Book):
    resp = await client.get(f"/api/v1/books/{book.id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == str(book.id)
    assert resp.json()["title"] == book.title


@pytest.mark.asyncio
async def test_get_nonexistent_book(client: AsyncClient):
    resp = await client.get(f"/api/v1/books/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_book(client: AsyncClient, book: Book):
    resp = await client.delete(f"/api/v1/books/{book.id}")
    assert resp.status_code == 204

    # Verify it's gone
    get_resp = await client.get(f"/api/v1/books/{book.id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_create_book_missing_title(client: AsyncClient):
    resp = await client.post("/api/v1/books", json={"isbn": "123"})
    assert resp.status_code == 422  # Unprocessable entity


@pytest.mark.asyncio
async def test_trigger_ingestion(client: AsyncClient, book: Book):
    """Triggering an ingestion job returns 202 with job details."""
    from unittest.mock import patch, MagicMock

    mock_task = MagicMock()
    mock_task.id = "celery-test-task-id"

    with patch(
        "app.api.jobs.run_ingestion_job.delay",
        return_value=mock_task,
    ):
        resp = await client.post(f"/api/v1/books/{book.id}/ingest")

    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] == "queued"
    assert data["book_id"] == str(book.id)
    assert data["celery_task_id"] == "celery-test-task-id"


@pytest.mark.asyncio
async def test_trigger_ingestion_conflict(client: AsyncClient, book: Book, db: AsyncSession):
    """Triggering a second ingestion while one is running returns 409."""
    from app.models.ingestion_job import IngestionJob

    running_job = IngestionJob(
        id=uuid.uuid4(),
        book_id=book.id,
        author_id=book.author_id,
        status="running",
    )
    db.add(running_job)
    await db.flush()

    resp = await client.post(f"/api/v1/books/{book.id}/ingest")
    assert resp.status_code == 409
