"""
Test configuration and shared fixtures.

Test database strategy
----------------------
Tests use a real PostgreSQL database (reviewpulse_test) with a fresh
nested transaction (SAVEPOINT) per test that is always rolled back.
This gives true isolation without DDL overhead per test.

Dependency overrides
--------------------
`get_db` is overridden in AsyncClient fixtures so all endpoint code
uses the same test transaction, which is rolled back after each test.

Running tests
-------------
    createdb reviewpulse_test
    cd backend && pytest tests/ -v
"""

from __future__ import annotations

import asyncio
import uuid
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.db.base import Base, get_db
from app.main import app
from app.models.author import Author
from app.models.book import Book
from app.models.review import Review

# Derive test DB URL by swapping the DB name
_db_url = settings.database_url
TEST_DATABASE_URL = (
    _db_url.rsplit("/reviewpulse", 1)[0] + "/reviewpulse_test"
    if "/reviewpulse" in _db_url
    else _db_url + "_test"
)

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables():
    """Create schema once per session, drop all tables after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    """Per-test DB session that always rolls back."""
    async with TestSessionLocal() as session:
        async with session.begin():
            yield session
            await session.rollback()


@pytest_asyncio.fixture
async def author(db: AsyncSession) -> Author:
    a = Author(
        id=uuid.uuid4(),
        email=f"test_{uuid.uuid4().hex[:8]}@example.com",
        hashed_password=hash_password("TestPass123"),
        display_name="Test Author",
    )
    db.add(a)
    await db.flush()
    return a


@pytest_asyncio.fixture
async def author_token(author: Author) -> str:
    return create_access_token(str(author.id))


@pytest_asyncio.fixture
async def another_author(db: AsyncSession) -> Author:
    """A second, unrelated author for multi-tenant isolation tests."""
    a = Author(
        id=uuid.uuid4(),
        email=f"other_{uuid.uuid4().hex[:8]}@example.com",
        hashed_password=hash_password("OtherPass456"),
        display_name="Other Author",
    )
    db.add(a)
    await db.flush()
    return a


@pytest_asyncio.fixture
async def another_token(another_author: Author) -> str:
    return create_access_token(str(another_author.id))


@pytest_asyncio.fixture
async def book(db: AsyncSession, author: Author) -> Book:
    b = Book(
        id=uuid.uuid4(),
        author_id=author.id,
        title="Test Novel: A Journey",
        isbn="9781234567890",
    )
    db.add(b)
    await db.flush()
    return b


@pytest_asyncio.fixture
async def analysed_review(db: AsyncSession, book: Book, author: Author) -> Review:
    """A review that has already been through LLM analysis."""
    r = Review(
        id=uuid.uuid4(),
        book_id=book.id,
        author_id=author.id,
        external_id="test-ext-001",
        reviewer_name="Jane D",
        rating=5,
        body="This book was absolutely wonderful. The characters are well developed and the pacing kept me engaged.",
        source="synthetic",
        sentiment="positive",
        sentiment_confidence=0.92,
        themes=["characters", "pacing"],
        is_ai_generated=False,
        ai_generated_confidence=0.05,
        summary="Reviewer praises character development and pacing.",
        is_actionable=False,
    )
    db.add(r)
    await db.flush()
    return r


@pytest_asyncio.fixture
async def client(db: AsyncSession, author_token: str) -> AsyncGenerator[AsyncClient, None]:
    """Authenticated AsyncClient — uses test DB session via dependency override."""

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {author_token}"},
    ) as c:
        yield c

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client_other(db: AsyncSession, another_token: str) -> AsyncGenerator[AsyncClient, None]:
    """Authenticated AsyncClient for the second (other) author."""

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {another_token}"},
    ) as c:
        yield c

    app.dependency_overrides.clear()


# ------------------------------------------------------------------ #
# Shared mock data fixtures (no DB required)
# ------------------------------------------------------------------ #

@pytest.fixture
def sample_review_text() -> str:
    return (
        "This book was absolutely wonderful. The characters are so well "
        "developed and the pacing kept me engaged throughout. "
        "The ending surprised me in the best way. Highly recommend!"
    )


@pytest.fixture
def sample_analysis_result() -> dict:
    return {
        "sentiment": "positive",
        "sentiment_confidence": 0.92,
        "themes": ["characters", "pacing", "ending"],
        "is_ai_generated": False,
        "ai_generated_confidence": 0.05,
        "summary": "Reviewer praises character development and pacing.",
        "is_actionable": False,
        "actionable_reason": None,
    }
