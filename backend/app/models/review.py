"""
Review model with pgvector embedding column.

The `embedding` column stores a 1536-dimensional float32 vector produced
by the OpenAI text-embedding-3-small model (or the configured provider).
This enables cosine-similarity semantic search across all reviews.

Idempotency
-----------
`external_id` is a stable identifier derived from the review source
(e.g. Amazon review ID or a hash of author+title+body for synthetic reviews).
A unique constraint on (book_id, external_id) prevents duplicate ingestion
regardless of how many times a job runs.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.book import Book


class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (
        # Idempotency guarantee — same review from the same book = same row
        UniqueConstraint("book_id", "external_id", name="uq_reviews_book_external"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    book_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("books.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # author_id is denormalised here for cheap single-table tenant filtering
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("authors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Source fields
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    reviewer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-5
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    review_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    verified_purchase: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String(50), default="synthetic")

    # LLM analysis fields — null until analysis job completes
    sentiment: Mapped[str | None] = mapped_column(
        String(20), nullable=True, index=True
    )  # "positive" | "mixed" | "negative"
    sentiment_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    themes: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    is_ai_generated: Mapped[bool | None] = mapped_column(Boolean, nullable=True, index=True)
    ai_generated_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_actionable: Mapped[bool | None] = mapped_column(Boolean, nullable=True, index=True)
    actionable_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Raw LLM response stored for debugging / reprocessing
    analysis_raw: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # pgvector embedding — stored as a raw ARRAY(Float) and cast in queries
    # We use a Text column storing the vector literal for maximum compatibility
    # with different pgvector versions; coerced at query time.
    embedding: Mapped[list[float] | None] = mapped_column(
        ARRAY(Float), nullable=True
    )

    analyzed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    book: Mapped["Book"] = relationship("Book", back_populates="reviews")
