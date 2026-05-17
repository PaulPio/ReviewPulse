"""LLM provider protocol and shared types."""

from __future__ import annotations

from typing import Literal, Protocol
from pydantic import BaseModel, Field


class ReviewAnalysis(BaseModel):
    """Structured output from LLM review analysis."""
    sentiment: Literal["positive", "mixed", "negative"]
    sentiment_confidence: float = Field(ge=0, le=1)
    themes: list[str] = Field(max_length=5)
    is_ai_generated: bool
    ai_generated_confidence: float = Field(ge=0, le=1)
    summary: str
    is_actionable: bool
    actionable_reason: str | None = None


class LLMProvider(Protocol):
    """Protocol for LLM providers."""

    async def analyze_review(self, review_text: str, book_title: str) -> ReviewAnalysis: ...
    def get_provider_name(self) -> str: ...
