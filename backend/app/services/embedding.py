"""
Text embedding service for semantic search (F4).

Supports two providers, both via the OpenAI SDK (compatible API):
  - openai     : direct OpenAI API  (model: "text-embedding-3-small")
  - openrouter : OpenRouter gateway (model resolved as "openai/text-embedding-3-small")

Default in settings is OpenRouter; set EMBEDDING_PROVIDER=openai for direct OpenAI.
The model name is automatically prefixed with "openai/" when using OpenRouter
if it isn't already.

Vectors are 1536-dimensional float32, stored as ARRAY(Float) in PostgreSQL
and cast to ::vector for cosine similarity search.
"""

from __future__ import annotations

import openai

from app.core.config import settings
from app.core.logging import get_logger
from app.services.llm.base import LLMError, calculate_cost_usd_micros

logger = get_logger(__name__)

_client: openai.AsyncOpenAI | None = None


def _get_client() -> openai.AsyncOpenAI:
    global _client
    if _client is None:
        if settings.embedding_provider == "openrouter":
            _client = openai.AsyncOpenAI(
                api_key=settings.openrouter_api_key,
                base_url="https://openrouter.ai/api/v1",
                default_headers={
                    "HTTP-Referer": "https://reviewpulse.app",
                    "X-Title": "ReviewPulse",
                },
            )
        else:
            _client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


def _resolve_model() -> str:
    """OpenRouter requires the 'openai/' provider prefix on the model slug."""
    model = settings.embedding_model
    if settings.embedding_provider == "openrouter" and not model.startswith("openai/"):
        return f"openai/{model}"
    return model


async def embed_text(text: str) -> tuple[list[float], int, int]:
    """
    Embed *text* and return (vector, prompt_tokens, cost_usd_micros).

    Raises openai.OpenAIError on failure — caller should catch and skip.
    """
    client = _get_client()
    model = _resolve_model()
    try:
        resp = await client.embeddings.create(
            model=model,
            input=text,
            dimensions=settings.embedding_dimensions,
        )
        vector = resp.data[0].embedding
        tokens = resp.usage.prompt_tokens
        cost_micros, _ = calculate_cost_usd_micros(
            provider=settings.embedding_provider,
            model=model,
            prompt_tokens=tokens,
            completion_tokens=0,
        )
        logger.debug(
            "embedding.created",
            provider=settings.embedding_provider,
            model=model,
            tokens=tokens,
            dimensions=len(vector),
        )
        return vector, tokens, cost_micros
    except openai.OpenAIError as exc:
        logger.error("embedding.failed", provider=settings.embedding_provider, error=str(exc))
        raise
