"""
OpenRouter client — drop-in using OpenAI SDK pointed at openrouter.ai.

OpenRouter exposes an OpenAI-compatible API so we reuse AsyncOpenAI with
a custom base_url. Model slugs follow the "provider/name" convention
(e.g. "google/gemini-2.0-flash-001", "anthropic/claude-3-5-haiku").

Costs are tracked under provider="openrouter" in LLMUsage. Because OpenRouter
returns usage in the same shape as OpenAI, no extra parsing is needed.
"""

from __future__ import annotations

import asyncio

import openai
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
    before_sleep_log,
)
import logging

from app.core.config import settings
from app.services.llm.base import BaseLLMClient, LLMError, LLMResponse

logger = logging.getLogger(__name__)

_RETRYABLE = (
    openai.RateLimitError,
    openai.APIStatusError,
    openai.APIConnectionError,
    openai.APITimeoutError,
    asyncio.TimeoutError,
)


class OpenRouterClient(BaseLLMClient):
    provider = "openrouter"

    def __init__(self, model: str | None = None) -> None:
        self.model = model or settings.openrouter_model
        self._client = openai.AsyncOpenAI(
            api_key=settings.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
            default_headers={
                "HTTP-Referer": "https://reviewpulse.app",
                "X-Title": "ReviewPulse",
            },
        )

    async def complete(self, prompt: str, system: str = "") -> LLMResponse:
        return await self._complete_with_retry(prompt=prompt, system=system)

    @retry(
        retry=retry_if_exception_type(_RETRYABLE),
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=1.0, max=60.0, jitter=2.0),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=False,
    )
    async def _complete_with_retry(self, prompt: str, system: str) -> LLMResponse:
        try:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            resp = await self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=1024,
            )

            choice = resp.choices[0]
            usage = resp.usage

            return LLMResponse(
                content=choice.message.content or "",
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0,
                total_tokens=usage.total_tokens if usage else 0,
                model=self.model,
                provider=self.provider,
                raw=resp,
            )
        except _RETRYABLE:
            raise
        except openai.APIError as exc:
            raise LLMError(
                f"OpenRouter API error: {exc}",
                provider=self.provider,
                cause=exc,
            )
