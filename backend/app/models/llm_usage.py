"""
LLMUsage tracks token counts and cost per LLM call (N3 requirement).

Cost calculation
----------------
Costs are stored in USD micro-dollars (integer) to avoid float precision
issues. Surface them by dividing by 1_000_000.

pricing_snapshot stores the per-token price in effect at call time,
so historical cost is always correct even if prices change.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LLMUsage(Base):
    __tablename__ = "llm_usage"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("authors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    book_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("books.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    review_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reviews.id", ondelete="SET NULL"),
        nullable=True,
    )

    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    operation: Mapped[str] = mapped_column(String(100), nullable=False)  # "analyze_review" | "embed" | "generate_synthetic"

    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)

    # Cost in USD micro-dollars (integer). Divide by 1_000_000 for USD.
    cost_usd_micros: Mapped[int] = mapped_column(BigInteger, default=0)

    # Snapshot of per-1K-token prices used for this call
    pricing_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
