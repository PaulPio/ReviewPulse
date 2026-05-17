"""
IngestionJob tracks the lifecycle of an async ingest + analysis pipeline run.

State machine
-------------
queued → running → completed
                 ↘ failed
                 ↘ partial   (some reviews analysed, some errored)

The `celery_task_id` links back to the Celery task for status queries.
`progress_*` fields allow a UI progress bar without polling Celery.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

JobStatus = Literal["queued", "running", "completed", "failed", "partial"]


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    book_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("books.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("authors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="queued", index=True
    )
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    # Progress counters
    total_reviews: Mapped[int] = mapped_column(Integer, default=0)
    processed_reviews: Mapped[int] = mapped_column(Integer, default=0)
    failed_reviews: Mapped[int] = mapped_column(Integer, default=0)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Detailed per-review error log for N4 observability
    error_details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationship
    book: Mapped["Book"] = relationship("Book", back_populates="ingestion_jobs")  # type: ignore[name-defined]
