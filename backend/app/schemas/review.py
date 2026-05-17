"""Pydantic v2 schemas for Review endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field


SentimentType = Literal["positive", "mixed", "negative"]


class ReviewOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    book_id: uuid.UUID
    author_id: uuid.UUID
    external_id: str
    reviewer_name: str | None
    rating: int | None
    title: str | None
    body: str
    review_date: datetime | None
    verified_purchase: bool
    source: str

    # Analysis
    sentiment: SentimentType | None
    sentiment_confidence: float | None
    themes: list[str] | None
    is_ai_generated: bool | None
    ai_generated_confidence: float | None
    summary: str | None
    is_actionable: bool | None
    actionable_reason: str | None

    analyzed_at: datetime | None
    created_at: datetime


class ReviewFilter(BaseModel):
    """Query parameters for filtering the reviews list endpoint."""
    sentiment: SentimentType | None = None
    is_ai_generated: bool | None = None
    is_actionable: bool | None = None
    theme: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    sort_by: Literal["review_date", "rating", "created_at", "sentiment_confidence"] = "review_date"
    sort_order: Literal["asc", "desc"] = "desc"
    page: Annotated[int, Field(ge=1)] = 1
    page_size: Annotated[int, Field(ge=1, le=100)] = 20


class ReviewPage(BaseModel):
    items: list[ReviewOut]
    total: int
    page: int
    page_size: int
    pages: int


class SemanticSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    top_k: Annotated[int, Field(ge=1, le=50)] = 10
    book_ids: list[uuid.UUID] | None = None  # None = search all author's books


class SemanticSearchResult(BaseModel):
    review_id: uuid.UUID
    book_id: uuid.UUID
    book_title: str
    snippet: str  # First 300 chars of body
    score: float  # cosine similarity 0..1
    sentiment: SentimentType | None
    review_date: datetime | None
    rating: int | None


class SemanticSearchResponse(BaseModel):
    query: str
    results: list[SemanticSearchResult]
    total_searched: int  # how many vectors were scanned
