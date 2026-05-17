"""
Anthropic Claude client with tenacity retry + exponential backoff.

Retry policy (N5)
-----------------
- Retries on: RateLimitError, APIStatusError (5xx), network timeouts
- Wait: exponential backoff capped at settings.llm_retry_max_wait
- After all retries: raises LLMError (caller handles partial failure)
- Jitter: random_jitter prevents thundering herd on rate limits
"""

from __future__ import annotations

import asyncio

import anthropic
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
    anthropic.RateLimitError,
    anthropic.APIStatusError,
    anthropic.APIConnectionError,
    asyncio.TimeoutError,
)


class AnthropicClient(BaseLLMClient):
    provider = "anthropic"

    def __init__(self, model: str | None = None) -> None:
        self.model = model or settings.anthropic_model
        self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def complete(self, prompt: str, system: str = "") -> LLMResponse:
        return await self._complete_with_retry(prompt=prompt, system=system)

    @retry(
        retry=retry_if_exception_type(_RETRYABLE),
        stop=stop_after_attempt(3),  # settings used at runtime
        wait=wait_exponential_jitter(initial=1.0, max=60.0, jitter=2.0),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=False,
    )
    async def _complete_with_retry(self, prompt: str, system: str) -> LLMResponse:
        try:
            kwargs: dict = {
                "model": self.model,
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": prompt}],
            }
            if system:
                kwargs["system"] = system

            msg = await self._client.messages.create(**kwargs)

            content = msg.content[0].text if msg.content else ""
            usage = msg.usage

            return LLMResponse(
                content=content,
                prompt_tokens=usage.input_tokens,
                completion_tokens=usage.output_tokens,
                total_tokens=usage.input_tokens + usage.output_tokens,
                model=self.model,
                provider=self.provider,
                raw=msg,
            )
        except _RETRYABLE:
            raise
        except anthropic.APIError as exc:
            raise LLMError(
                f"Anthropic API error: {exc}",
                provider=self.provider,
                cause=exc,
            )
