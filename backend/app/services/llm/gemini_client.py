"""
Google Gemini client (third LLM implementation).

Uses the google-generativeai SDK directly.
Gemini Flash is the default — fast and very cheap for structured tasks.
"""

from __future__ import annotations

import asyncio

from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
    before_sleep_log,
)
import logging

from app.core.config import settings
from app.services.llm.base import BaseLLMClient, LLMError, LLMResponse

logger = logging.getLogger(__name__)


def _is_retryable(exc: BaseException) -> bool:
    """Gemini SDK doesn't have typed exceptions; check message."""
    msg = str(exc).lower()
    return any(k in msg for k in ("rate limit", "quota", "503", "502", "timeout", "unavailable"))


class GeminiClient(BaseLLMClient):
    provider = "gemini"

    def __init__(self, model: str | None = None) -> None:
        self.model = model or settings.gemini_model
        self._configured = False

    def _configure(self) -> None:
        if not self._configured:
            import google.generativeai as genai
            genai.configure(api_key=settings.gemini_api_key)
            self._genai = genai
            self._configured = True

    async def complete(self, prompt: str, system: str = "") -> LLMResponse:
        return await self._complete_with_retry(prompt=prompt, system=system)

    @retry(
        retry=retry_if_exception(_is_retryable),
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=1.0, max=60.0, jitter=2.0),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=False,
    )
    async def _complete_with_retry(self, prompt: str, system: str) -> LLMResponse:
        self._configure()
        try:
            model = self._genai.GenerativeModel(
                model_name=self.model,
                system_instruction=system or None,
            )

            # Gemini SDK is sync; run in executor to avoid blocking the event loop
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: model.generate_content(prompt),
            )

            content = response.text or ""
            # Gemini usage metadata
            usage_meta = getattr(response, "usage_metadata", None)
            prompt_tokens = getattr(usage_meta, "prompt_token_count", 0) or 0
            completion_tokens = getattr(usage_meta, "candidates_token_count", 0) or 0

            return LLMResponse(
                content=content,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                model=self.model,
                provider=self.provider,
                raw=response,
            )
        except Exception as exc:
            if _is_retryable(exc):
                raise
            raise LLMError(
                f"Gemini API error: {exc}",
                provider=self.provider,
                cause=exc,
            )
