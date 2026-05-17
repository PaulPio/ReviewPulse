import enum
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

if TYPE_CHECKING:
    pass


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class JobStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"
    partial = "partial"


class JobKind(str, enum.Enum):
    ingest_book = "ingest_book"


class Author(Base):
    __tablename__ = "authors"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    supabase_user_id: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    display_name: Mapped[str] = mapped_column(String(200), default="Author")
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    books: Mapped[list["Book"]] = relationship(back_populates="author")
    jobs: Mapped[list["Job"]] = relationship(back_populates="author")


class Book(Base):
    __tablename__ = "books"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("authors.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(500))
    isbn: Mapped[str | None] = mapped_column(String(32), nullable=True)
    asin: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    catalog_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    author: Mapped["Author"] = relationship(back_populates="books")
    reviews: Mapped[list["Review"]] = relationship(back_populates="book")


class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (UniqueConstraint("book_id", "external_key", name="uq_review_book_external"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    book_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("books.id", ondelete="CASCADE"), index=True
    )
    external_key: Mapped[str] = mapped_column(String(128))
    body: Mapped[str] = mapped_column(Text())
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    review_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    embedding: Mapped[Any | None] = mapped_column(Vector(1536), nullable=True)

    book: Mapped["Book"] = relationship(back_populates="reviews")
    analysis: Mapped["ReviewAnalysis | None"] = relationship(back_populates="review", uselist=False)


class ReviewAnalysis(Base):
    __tablename__ = "review_analyses"

    review_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("reviews.id", ondelete="CASCADE"), primary_key=True
    )
    sentiment: Mapped[str] = mapped_column(String(32))
    sentiment_confidence: Mapped[float] = mapped_column()
    themes: Mapped[list[Any]] = mapped_column(JSON, default=list)
    ai_generated: Mapped[bool] = mapped_column()
    ai_generated_confidence: Mapped[float] = mapped_column()
    summary: Mapped[str] = mapped_column(Text())
    actionable: Mapped[bool] = mapped_column()
    prompt_tokens: Mapped[int] = mapped_column(default=0)
    completion_tokens: Mapped[int] = mapped_column(default=0)
    estimated_cost_usd: Mapped[float] = mapped_column(default=0.0)
    model_id: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    review: Mapped["Review"] = relationship(back_populates="analysis")


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint(
            "author_id",
            "book_id",
            "idempotency_key",
            name="uq_jobs_author_book_idempotency_key",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("authors.id", ondelete="CASCADE"), index=True
    )
    book_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("books.id", ondelete="SET NULL"), nullable=True
    )
    kind: Mapped[JobKind] = mapped_column(
        SQLEnum(JobKind, native_enum=False, values_callable=lambda e: [m.value for m in e])
    )
    status: Mapped[JobStatus] = mapped_column(
        SQLEnum(JobStatus, native_enum=False, values_callable=lambda e: [m.value for m in e]),
        default=JobStatus.queued,
    )
    error_message: Mapped[str | None] = mapped_column(Text(), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    job_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    author: Mapped["Author"] = relationship(back_populates="jobs")
