from unittest.mock import patch

from app.models import Book


@patch("app.api.books_routes.run_ingest_job.delay")
def test_ingest_idempotency_returns_same_job(mock_delay, client, author_a, db_session):
    book = Book(author_id=author_a.id, title="T", asin="DEMOX")
    db_session.add(book)
    db_session.commit()
    db_session.refresh(book)

    headers = {
        "X-Dev-Author-Id": str(author_a.id),
        "Idempotency-Key": "same-key",
    }
    r1 = client.post(f"/api/v1/books/{book.id}/ingest", headers=headers)
    r2 = client.post(f"/api/v1/books/{book.id}/ingest", headers=headers)
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["id"] == r2.json()["id"]
    assert mock_delay.call_count == 1


@patch("app.api.books_routes.run_ingest_job.delay")
def test_ingest_distinct_keys_enqueue_twice(mock_delay, client, author_a, db_session):
    book = Book(author_id=author_a.id, title="T2", asin="DEMOY")
    db_session.add(book)
    db_session.commit()
    db_session.refresh(book)

    base = {"X-Dev-Author-Id": str(author_a.id)}
    r1 = client.post(
        f"/api/v1/books/{book.id}/ingest",
        headers={**base, "Idempotency-Key": "a"},
    )
    r2 = client.post(
        f"/api/v1/books/{book.id}/ingest",
        headers={**base, "Idempotency-Key": "b"},
    )
    assert r1.json()["id"] != r2.json()["id"]
    assert mock_delay.call_count == 2


def test_ingest_without_key_always_new_jobs(client, author_a, db_session):
    with patch("app.api.books_routes.run_ingest_job.delay"):
        book = Book(author_id=author_a.id, title="T3", asin="DEMOZ")
        db_session.add(book)
        db_session.commit()
        db_session.refresh(book)
        base = {"X-Dev-Author-Id": str(author_a.id)}
        r1 = client.post(f"/api/v1/books/{book.id}/ingest", headers=base)
        r2 = client.post(f"/api/v1/books/{book.id}/ingest", headers=base)
        assert r1.json()["id"] != r2.json()["id"]
