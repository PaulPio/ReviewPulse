"""
Unit tests for the analysis service (N6 requirement).

Tests verify:
1. AnalysisResult Pydantic model validates correctly
2. analyze_review() calls the LLM and parses results (mock LLM)
3. Fallback logic is triggered when primary provider fails
4. All-provider failure raises LLMError cleanly
5. Invalid JSON from LLM raises LLMError (not an unhandled crash)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.services.analysis import AnalysisResult, analyze_review
from app.services.llm.base import LLMError, LLMResponse


def _make_response(content: str, provider: str = "anthropic") -> LLMResponse:
    return LLMResponse(
        content=content,
        prompt_tokens=150,
        completion_tokens=80,
        total_tokens=230,
        model="claude-3-5-haiku-20241022",
        provider=provider,
    )


_VALID_PARSED = {
    "sentiment": "positive",
    "sentiment_confidence": 0.92,
    "themes": ["characters", "pacing"],
    "is_ai_generated": False,
    "ai_generated_confidence": 0.05,
    "summary": "Reviewer praises character development and pacing.",
    "is_actionable": False,
    "actionable_reason": None,
}


class TestAnalysisResult:
    """Unit tests for the AnalysisResult Pydantic model (no I/O)."""

    def test_valid_positive_review(self, sample_analysis_result):
        result = AnalysisResult.model_validate(sample_analysis_result)
        assert result.sentiment == "positive"
        assert result.sentiment_confidence == 0.92
        assert "characters" in result.themes
        assert result.is_ai_generated is False
        assert result.is_actionable is False

    def test_invalid_sentiment_rejected(self):
        bad = {**_VALID_PARSED, "sentiment": "lukewarm"}
        with pytest.raises(Exception):
            AnalysisResult.model_validate(bad)

    def test_confidence_above_one_rejected(self):
        bad = {**_VALID_PARSED, "sentiment_confidence": 1.5}
        with pytest.raises(Exception):
            AnalysisResult.model_validate(bad)

    def test_confidence_below_zero_rejected(self):
        bad = {**_VALID_PARSED, "sentiment_confidence": -0.1}
        with pytest.raises(Exception):
            AnalysisResult.model_validate(bad)

    def test_duplicate_themes_deduplicated(self):
        data = {**_VALID_PARSED, "themes": ["pacing", "pacing", "characters"]}
        result = AnalysisResult.model_validate(data)
        assert result.themes == ["pacing", "characters"]

    def test_actionable_review_has_reason(self):
        data = {
            **_VALID_PARSED,
            "sentiment": "mixed",
            "is_actionable": True,
            "actionable_reason": "Fix the ending",
        }
        result = AnalysisResult.model_validate(data)
        assert result.is_actionable is True
        assert result.actionable_reason == "Fix the ending"


@pytest.mark.asyncio
class TestAnalyzeReviewFunction:
    """Tests for analyze_review() with mocked LLM clients."""

    async def test_successful_analysis(self, sample_review_text):
        mock_client = AsyncMock()
        mock_client.provider = "anthropic"
        mock_client.model = "claude-3-5-haiku-20241022"
        mock_client.complete_json = AsyncMock(
            return_value=(_VALID_PARSED, _make_response("..."))
        )

        with patch(
            "app.services.analysis.get_llm_client_with_fallback",
            return_value=(mock_client, None),
        ):
            result, llm_resp = await analyze_review(
                review_body=sample_review_text,
                book_title="Test Novel",
                reviewer_name="Jane D",
                rating=5,
            )

        assert result.sentiment == "positive"
        assert result.sentiment_confidence == 0.92
        assert "characters" in result.themes
        assert result.is_ai_generated is False
        assert llm_resp.total_tokens == 230

    async def test_fallback_on_primary_failure(self, sample_review_text):
        """When the primary provider fails, the fallback is used."""
        primary = AsyncMock()
        primary.provider = "anthropic"
        primary.complete_json = AsyncMock(
            side_effect=LLMError("rate limit", provider="anthropic")
        )

        fallback_parsed = {**_VALID_PARSED, "sentiment_confidence": 0.85}
        fallback = AsyncMock()
        fallback.provider = "openai"
        fallback.complete_json = AsyncMock(
            return_value=(fallback_parsed, _make_response("...", provider="openai"))
        )

        with patch(
            "app.services.analysis.get_llm_client_with_fallback",
            return_value=(primary, fallback),
        ):
            result, llm_resp = await analyze_review(
                review_body=sample_review_text,
                book_title="Test Novel",
            )

        assert result.sentiment == "positive"
        assert result.sentiment_confidence == 0.85
        # LLMError from primary was caught; fallback was used
        primary.complete_json.assert_called_once()
        fallback.complete_json.assert_called_once()

    async def test_all_providers_fail_raises_llm_error(self, sample_review_text):
        """When all providers fail, LLMError propagates to caller."""
        primary = AsyncMock()
        primary.provider = "anthropic"
        primary.complete_json = AsyncMock(
            side_effect=LLMError("rate limit", provider="anthropic")
        )
        fallback = AsyncMock()
        fallback.provider = "openai"
        fallback.complete_json = AsyncMock(
            side_effect=LLMError("quota exceeded", provider="openai")
        )

        with patch(
            "app.services.analysis.get_llm_client_with_fallback",
            return_value=(primary, fallback),
        ):
            with pytest.raises(LLMError):
                await analyze_review(
                    review_body=sample_review_text,
                    book_title="Test Novel",
                )

    async def test_no_fallback_configured(self, sample_review_text):
        """With no fallback configured, failure raises LLMError immediately."""
        primary = AsyncMock()
        primary.provider = "anthropic"
        primary.complete_json = AsyncMock(
            side_effect=LLMError("rate limit", provider="anthropic")
        )

        with patch(
            "app.services.analysis.get_llm_client_with_fallback",
            return_value=(primary, None),
        ):
            with pytest.raises(LLMError):
                await analyze_review(
                    review_body=sample_review_text,
                    book_title="Test Novel",
                )
