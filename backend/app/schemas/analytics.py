"""Pydantic v2 schemas for analytics endpoints (trends, comparison, digest)."""

from __future__ import annotations

import uuid
from datetime import datetime, date

from pydantic import BaseModel, Field


# ------------------------------------------------------------------ #
# Trend metrics (F5)
# ------------------------------------------------------------------ #

class SentimentDataPoint(BaseModel):
    week_start: date
    positive: int
    mixed: int
    negative: int
    total: int
    positive_pct: float
    week_over_week_delta: float | None = None  # change in positive_pct vs prior week


class ThemeDataPoint(BaseModel):
    week_start: date
    theme: str
    count: int
    delta: int | None = None  # change vs prior week


class TrendResponse(BaseModel):
    book_id: uuid.UUID
    book_title: str
    sentiment_series: list[SentimentDataPoint]
    theme_series: list[ThemeDataPoint]
    rising_themes: list[str]
    falling_themes: list[str]


# ------------------------------------------------------------------ #
# Cross-book comparison (F6)
# ------------------------------------------------------------------ #

class BookComparisonItem(BaseModel):
    book_id: uuid.UUID
    book_title: str
    total_reviews: int
    avg_rating: float | None
    sentiment_positive_pct: float
    sentiment_mixed_pct: float
    sentiment_negative_pct: float
    top_themes: list[str]
    ai_flagged_rate: float
    actionable_rate: float
    review_velocity: float  # reviews per week (last 4 weeks)


class ComparisonResponse(BaseModel):
    book_ids: list[uuid.UUID]
    items: list[BookComparisonItem]


# ------------------------------------------------------------------ #
# "What's new since I last logged in" (F8)
# ------------------------------------------------------------------ #

class NewSinceLoginItem(BaseModel):
    book_id: uuid.UUID
    book_title: str
    new_review_count: int
    sentiment_shift: str | None  # "improving" | "declining" | "stable"
    top_new_themes: list[str]
    most_notable_review_id: uuid.UUID | None
    most_notable_review_summary: str | None


class NewSinceLoginResponse(BaseModel):
    since: datetime
    total_new_reviews: int
    items: list[NewSinceLoginItem]
    has_activity: bool


# ------------------------------------------------------------------ #
# Weekly digest (F10)
# ------------------------------------------------------------------ #

class DigestReviewSnippet(BaseModel):
    rating: int | None
    sentiment: str | None
    summary: str
    reviewer_name: str | None
    review_date: datetime | None


class DigestBookSection(BaseModel):
    book_id: uuid.UUID
    book_title: str
    new_reviews: int
    avg_rating: float | None
    sentiment_summary: str  # e.g. "80% positive, up from 70% last week"
    top_themes: list[str]
    notable_reviews: list[DigestReviewSnippet]
    actionable_count: int
    actionable_highlights: list[str]


class WeeklyDigestResponse(BaseModel):
    author_name: str
    period_start: date
    period_end: date
    total_new_reviews: int
    overall_sentiment_trend: str  # "improving" | "stable" | "declining"
    books: list[DigestBookSection]
    ai_flagged_alert: str | None  # if ai-flagged rate spiked
    cost_this_week_usd: float


# ------------------------------------------------------------------ #
# LLM cost summary (N3)
# ------------------------------------------------------------------ #

class CostSummary(BaseModel):
    author_id: uuid.UUID
    total_cost_usd: float
    total_tokens: int
    by_book: list[dict]  # [{book_id, book_title, cost_usd, tokens}]
    by_provider: list[dict]  # [{provider, cost_usd, tokens}]
