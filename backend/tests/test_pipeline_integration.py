from app.models import Book, Review
from app.llm.mock import MockLLMClient


def test_analyze_and_embed_happy_path(db_session, author_a):
    book = Book(author_id=author_a.id, title="Demo", asin="DEMOASIN01")
    db_session.add(book)
    db_session.commit()
    db_session.refresh(book)

    r = Review(book_id=book.id, external_key="x1", body="Great book, amazing characters.", rating=5)
    db_session.add(r)
    db_session.commit()
    db_session.refresh(r)

    from app.tasks import analyze_if_needed

    llm = MockLLMClient()
    analyze_if_needed(db_session, r.id, llm)
    db_session.refresh(r)
    assert r.analysis is not None
    assert r.analysis.sentiment in ("positive", "mixed", "negative")
    assert r.embedding is not None
