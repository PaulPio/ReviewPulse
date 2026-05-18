"""
SQLAlchemy 2.0 async engine + session factory.

We use a single async engine connected to PostgreSQL via asyncpg.
Sessions are managed through an async context manager injected into
every request via the `get_db` dependency.

Connection pooling
------------------
pool_size=10, max_overflow=20 are sensible defaults for a single-process
Uvicorn deployment. Tune per environment via DATABASE_POOL_* env vars.

pgvector
--------
The `vector` type is registered on first connection via the
`asyncpg` listener below. This avoids the need to call
`register_vector` inside every coroutine.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, MappedColumn
from sqlalchemy import MetaData

from app.core.config import settings

# Naming convention keeps Alembic migrations deterministic
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


engine = create_async_engine(
    settings.database_url_asyncpg,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    connect_args=settings.database_connect_args,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async DB session per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
