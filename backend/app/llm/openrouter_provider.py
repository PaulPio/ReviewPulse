"""OpenRouter LLM provider - primary provider using cheapest models."""

from __future__ import annotations

import json
import httpx
import structlog

from app.core.config import settings
from app.llm.base import ReviewAnalysis

logger = structlog.get_logger()

ANALYSIS_SYSTEM_PROMPT = """You are a book review analyst. Analyze the given review and return a JSON object with these exact fields:
- sentiment: "positive", "mixed", or "negative"
- sentiment_confidence: float 0-1
- themes: list of up to 5 themes from [pacing, characters, ending, plot, writing_style, world_building, dialogue, cover, narration, editing, value, emotional_impact]
- is_ai_generated: boolean - true if the review appears AI-generated
- ai_generated_confidence: float 0-1
- summary: one sentence summary of the review's main point
- is_actionable: boolean - true if contains feedback the author can act on
- actionable_reason: string or null - what action could be taken

Be calibrated. Use 0.5 confidence for genuinely ambiguous cases. Return only valid JSON."""


class OpenRouterProvider:
    """Primary LLM provider using OpenRouter gateway."""

    def __init__(self):
        self.api_key = settings.anthropic_api_key or settings.openai_api_key
        self.base_url = "https://openrouter.ai/api/v1"
        self.model = settings.anthropic_model

    def get_provider_name(self) -> str:
        return "openrouter"

    async def analyze_review(self, review_text: str, book_title: str) -> ReviewAnalysis:
        user_prompt = f"Book: {book_title}\n\nReview:\n{review_text[:3000]}"

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.1,
                    "max_tokens": 500,
                },
            )
            response.raise_for_status()
            data = response.json()

        content = data["choices"][0]["message"]["content"]
        # Parse JSON from response
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code block
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            parsed = json.loads(content)

        return ReviewAnalysis(**parsed)
