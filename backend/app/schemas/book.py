"""Pydantic v2 schemas for Book endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import AnyHttpUrl, BaseModel, Field


class BookCreate(BaseModel):
    title: str = Field(min_length=1, max_length=512)
    isbn: str | None = Field(default=None, max_length=20)
    asin: str | None = Field(default=None, max_length=20)
    amazon_url: str | None = None
    cover_url: str | None = None
    description: str | None = None
    published_at: datetime | None = None


class BookUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=512)
    isbn: str | None = None
    asin: str | None = None
    amazon_url: str | None = None
    cover_url: str | None = None
    description: str | None = None
    published_at: datetime | None = None


class BookOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    author_id: uuid.UUID
    title: str
    isbn: str | None
    asin: str | None
    amazon_url: str | None
    cover_url: str | None
    description: str | None
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime


class BookWithStats(BookOut):
    """BookOut extended with aggregated review statistics."""
    total_reviews: int = 0
    avg_rating: float | None = None
    sentiment_positive: int = 0
    sentiment_mixed: int = 0
    sentiment_negative: int = 0
    ai_flagged_count: int = 0
    actionable_count: int = 0
    last_review_at: datetime | None = None
    total_cost_usd: float = 0.0
