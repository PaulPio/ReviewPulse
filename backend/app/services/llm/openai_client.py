"""
OpenAI client with tenacity retry + exponential backoff.

Uses the openai Python SDK directly — no LangChain, no wrapper frameworks.
JSON mode is enabled via `response_format={"type": "json_object"}` when
the system prompt instructs JSON output.
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


class OpenAIClient(BaseLLMClient):
    provider = "openai"

    def __init__(self, model: str | None = None) -> None:
        self.model = model or settings.openai_model
        self._client = openai.AsyncOpenAI(api_key=settings.openai_api_key)

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

            # Enable JSON mode when the system prompt requests JSON
            extra_kwargs = {}
            if system and "json" in system.lower():
                extra_kwargs["response_format"] = {"type": "json_object"}

            resp = await self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=1024,
                **extra_kwargs,
            )

            choice = resp.choices[0]
            usage = resp.usage

            return LLMResponse(
                content=choice.message.content or "",
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                total_tokens=usage.total_tokens,
                model=self.model,
                provider=self.provider,
                raw=resp,
            )
        except _RETRYABLE:
            raise
        except openai.APIError as exc:
            raise LLMError(
                f"OpenAI API error: {exc}",
                provider=self.provider,
                cause=exc,
            )
