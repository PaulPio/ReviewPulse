"""
Author model — one row per registered user/tenant.

Multi-tenant isolation
----------------------
Every sensitive table (books, reviews, jobs) carries an `author_id` FK.
All repository queries filter on `author_id = current_author.id`, so
cross-tenant data leakage is structurally impossible at the query layer.
The boundary is enforced in:
  - SQLAlchemy queries  (repositories)
  - API dependencies    (app/api/deps.py → get_current_author)
  - Integration tests   (tests/test_isolation.py)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Author(Base):
    __tablename__ = "authors"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Supabase Auth UID — optional; populated when auth is delegated to Supabase
    supabase_uid: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)

    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    books: Mapped[list["Book"]] = relationship(  # type: ignore[name-defined]
        "Book", back_populates="author", cascade="all, delete-orphan"
    )
