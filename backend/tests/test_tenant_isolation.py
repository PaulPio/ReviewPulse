from app.models import Book


def test_cannot_access_other_author_book(client, author_a, author_b, db_session):
    b = Book(author_id=author_a.id, title="Secret", asin="DEMOASIN01")
    db_session.add(b)
    db_session.commit()
    db_session.refresh(b)

    r = client.get(f"/api/v1/books/{b.id}/reviews", headers={"X-Dev-Author-Id": str(author_b.id)})
    assert r.status_code == 404


def test_search_returns_empty_for_other_author(client, author_a, author_b, db_session):
    # No embeddings in empty DB — search should still not leak; returns empty items
    r = client.post(
        "/api/v1/search",
        json={"query": "anything", "limit": 5},
        headers={"X-Dev-Author-Id": str(author_b.id)},
    )
    assert r.status_code == 200
    assert r.json()["items"] == []
