from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


class AuthorOut(BaseModel):
    id: uuid.UUID
    display_name: str
    email: str | None = None
    last_seen_at: datetime | None = None

    model_config = {"from_attributes": True}


class AuthorBootstrap(BaseModel):
    display_name: str = Field(min_length=1, max_length=200)


class BookCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    isbn: str | None = Field(default=None, max_length=32)
    asin: str | None = Field(default=None, max_length=32)
    catalog_url: str | None = Field(default=None, max_length=2000)


class BookOut(BaseModel):
    id: uuid.UUID
    title: str
    isbn: str | None
    asin: str | None
    catalog_url: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class BookCatalogOut(BookOut):
    """Catalog row with lightweight review stats for dashboard cards."""

    review_count: int = 0
    analyzed_count: int = 0
    pct_negative: float | None = None


class JobOut(BaseModel):
    id: uuid.UUID
    status: str
    kind: str
    book_id: uuid.UUID | None
    error_message: str | None
    idempotency_key: str | None = None
    job_data: dict
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class IngestionWebhookIn(BaseModel):
    book_id: uuid.UUID
    idempotency_key: str | None = Field(default=None, max_length=128)


class IngestionWebhookAck(BaseModel):
    job_id: uuid.UUID
    deduped: bool


class ReviewAnalysisOut(BaseModel):
    sentiment: str
    sentiment_confidence: float
    themes: list[str]
    ai_generated: bool
    ai_generated_confidence: float
    summary: str
    actionable: bool
    prompt_tokens: int
    completion_tokens: int
    estimated_cost_usd: float
    model_id: str

    model_config = {"from_attributes": True}


class ReviewOut(BaseModel):
    id: uuid.UUID
    book_id: uuid.UUID
    body: str
    rating: int | None
    review_date: datetime | None
    created_at: datetime
    analysis: ReviewAnalysisOut | None = None


class ReviewListResponse(BaseModel):
    items: list[ReviewOut]
    total: int
    page: int
    page_size: int


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=10, ge=1, le=50)


class SearchHit(BaseModel):
    review_id: uuid.UUID
    book_id: uuid.UUID
    book_title: str
    snippet: str
    score: float


class SearchResponse(BaseModel):
    items: list[SearchHit]


class CompareRequest(BaseModel):
    book_ids: list[uuid.UUID] = Field(min_length=2, max_length=4)


class ThemeCount(BaseModel):
    theme: str
    count: int


class CompareBookSummary(BaseModel):
    book_id: uuid.UUID
    title: str
    review_count: int
    sentiment_positive_pct: float
    sentiment_mixed_pct: float
    sentiment_negative_pct: float
    top_themes: list[ThemeCount]
    ai_flagged_pct: float
    reviews_per_week: float


class CompareResponse(BaseModel):
    books: list[CompareBookSummary]


class SpendSummary(BaseModel):
    total_estimated_cost_usd: float
    total_prompt_tokens: int
    total_completion_tokens: int
    by_book: dict[str, float]


class TrendPoint(BaseModel):
    period_start: date
    avg_sentiment_score: float
    review_count: int


class TrendsResponse(BaseModel):
    book_id: uuid.UUID
    granularity: Literal["week"]
    series: list[TrendPoint]
    theme_counts: list[ThemeCount]


class DigestReview(BaseModel):
    summary: str
    sentiment: str
    book_title: str


class DigestPreview(BaseModel):
    html: str


class WhatsNewItem(BaseModel):
    review_id: uuid.UUID
    book_title: str
    summary: str
    sentiment: str
    actionable: bool
    score: float
