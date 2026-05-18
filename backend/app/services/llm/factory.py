"""
LLM client factory.

`get_llm_client()` returns the primary provider's client.
`get_llm_client_with_fallback()` returns (primary, fallback | None).

Usage:
    client = get_llm_client()
    response = await client.complete(prompt, system)

Swap providers without code changes by setting LLM_PROVIDER in .env (code default: openrouter).
"""

from __future__ import annotations

from app.core.config import settings
from app.services.llm.base import BaseLLMClient


def _build_client(provider: str) -> BaseLLMClient:
    if provider == "anthropic":
        from app.services.llm.anthropic_client import AnthropicClient
        return AnthropicClient()
    if provider == "openai":
        from app.services.llm.openai_client import OpenAIClient
        return OpenAIClient()
    if provider == "gemini":
        from app.services.llm.gemini_client import GeminiClient
        return GeminiClient()
    if provider == "openrouter":
        from app.services.llm.openrouter_client import OpenRouterClient
        return OpenRouterClient()
    raise ValueError(f"Unknown LLM provider: {provider!r}")


def get_llm_client() -> BaseLLMClient:
    """Return the configured primary LLM client."""
    return _build_client(settings.llm_provider)


def get_llm_client_with_fallback() -> tuple[BaseLLMClient, BaseLLMClient | None]:
    """Return (primary_client, fallback_client | None)."""
    primary = _build_client(settings.llm_provider)
    fallback = (
        _build_client(settings.llm_fallback_provider)
        if settings.llm_fallback_provider
        else None
    )
    return primary, fallback
