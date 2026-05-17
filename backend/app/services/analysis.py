"""
Review analysis service.

Calls the configured LLM to extract structured intelligence from a review.

Output schema (Pydantic model validated before storage)
-------------------------------------------------------
{
  "sentiment": "positive" | "mixed" | "negative",
  "sentiment_confidence": 0.0-1.0,
  "themes": ["pacing", "characters", ...],
  "is_ai_generated": bool,
  "ai_generated_confidence": 0.0-1.0,
  "summary": "One sentence.",
  "is_actionable": bool,
  "actionable_reason": "Why the author should care."  // null if not actionable
}

The system prompt instructs the model to respond ONLY with valid JSON.
We validate the response with Pydantic before trusting it.

Fallback (N2 / N5)
-------------------
If the primary provider fails after retries, we try the fallback provider.
If both fail, we raise `LLMError` and the Celery task records the failure
against the individual review without killing the whole job.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.core.logging import get_logger
from app.services.llm.base import LLMError, LLMResponse
from app.services.llm.factory import get_llm_client_with_fallback

logger = get_logger(__name__)

ANALYSIS_SYSTEM_PROMPT = """You are a book review analyst. Analyse the user-supplied book review and return ONLY a valid JSON object with these exact keys:

- sentiment: one of "positive", "mixed", "negative"
- sentiment_confidence: float 0.0-1.0
- themes: array of strings from this list (only include mentioned ones): ["pacing", "characters", "plot", "writing_style", "ending", "world_building", "cover", "narration", "price", "length", "grammar", "translation", "emotional_impact", "humor", "romance", "mystery", "action", "research_accuracy"]
- is_ai_generated: boolean (true if the review reads like it was machine-written)
- ai_generated_confidence: float 0.0-1.0
- summary: single sentence (max 120 chars) summarising what the reviewer thought
- is_actionable: boolean (true if the review raises something the author could respond to or improve)
- actionable_reason: string or null — if actionable, one sentence explaining what the author should do

Return ONLY the JSON object. No markdown, no explanation."""


class AnalysisResult(BaseModel):
    sentiment: Literal["positive", "mixed", "negative"]
    sentiment_confidence: float = Field(ge=0.0, le=1.0)
    themes: list[str] = Field(default_factory=list)
    is_ai_generated: bool
    ai_generated_confidence: float = Field(ge=0.0, le=1.0)
    summary: str = Field(max_length=500)
    is_actionable: bool
    actionable_reason: str | None = None

    @field_validator("themes", mode="before")
    @classmethod
    def deduplicate_themes(cls, v: list) -> list:
        return list(dict.fromkeys(v))  # preserve order, remove dupes


async def analyze_review(
    review_body: str,
    book_title: str,
    reviewer_name: str | None = None,
    rating: int | None = None,
) -> tuple[AnalysisResult, LLMResponse]:
    """
    Analyse a single review.

    Returns (AnalysisResult, LLMResponse) so the caller can record token usage.
    Tries primary provider first, then fallback if configured.
    Raises LLMError if all providers fail.
    """
    primary, fallback = get_llm_client_with_fallback()

    context_parts = [f'Book: "{book_title}"']
    if reviewer_name:
        context_parts.append(f"Reviewer: {reviewer_name}")
    if rating is not None:
        context_parts.append(f"Star rating: {rating}/5")
    context_parts.append(f"\nReview text:\n{review_body}")
    prompt = "\n".join(context_parts)

    for client in filter(None, [primary, fallback]):
        try:
            data, llm_resp = await client.complete_json(
                prompt=prompt,
                system=ANALYSIS_SYSTEM_PROMPT,
            )
            result = AnalysisResult.model_validate(data)
            logger.info(
                "review.analysis_complete",
                provider=client.provider,
                model=client.model,
                tokens=llm_resp.total_tokens,
                sentiment=result.sentiment,
            )
            return result, llm_resp
        except LLMError as exc:
            logger.warning(
                "review.analysis_failed",
                provider=exc.provider,
                error=str(exc),
                will_try_fallback=fallback is not None and client is primary,
            )
            if client is not primary:
                raise

    raise LLMError(
        "All LLM providers failed for review analysis",
        provider="all",
    )
