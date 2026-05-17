"""Direct OpenAI provider - fallback provider."""

from __future__ import annotations

import json
import httpx
import structlog

from app.core.config import settings
from app.llm.base import ReviewAnalysis
from app.llm.openrouter_provider import ANALYSIS_SYSTEM_PROMPT

logger = structlog.get_logger()


class OpenAIProvider:
    """Fallback LLM provider using direct OpenAI API."""

    def __init__(self):
        self.api_key = settings.openai_api_key
        self.model = settings.openai_model

    def get_provider_name(self) -> str:
        return "openai"

    async def analyze_review(self, review_text: str, book_title: str) -> ReviewAnalysis:
        user_prompt = f"Book: {book_title}\n\nReview:\n{review_text[:3000]}"

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
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
                    "response_format": {"type": "json_object"},
                },
            )
            response.raise_for_status()
            data = response.json()

        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        return ReviewAnalysis(**parsed)
