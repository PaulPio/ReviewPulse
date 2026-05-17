"""
Text embedding service for semantic search (F4).

We use OpenAI's text-embedding-3-small (1536 dimensions) via the OpenAI SDK.
The resulting float32 vectors are stored in the Review.embedding column
(PostgreSQL ARRAY(Float)) and searched using cosine similarity in raw SQL.

Why not pgvector's ORM column type?
------------------------------------
pgvector's SQLAlchemy integration requires registering a custom type and
running `CREATE EXTENSION vector` before the ORM can map it. To keep the
setup simpler (and avoid a pgvector-specific ORM dependency), we:
  1. Store embeddings as ARRAY(Float) in the ORM model.
  2. Cast to ::vector in raw SQL queries for cosine similarity search.
This is fully compatible with pgvector and avoids version pinning on the
pgvector Python package's ORM integration.
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
        _client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


async def embed_text(text: str) -> tuple[list[float], int, int]:
    """
    Embed *text* and return (vector, prompt_tokens, cost_usd_micros).

    The text is truncated to 8191 tokens (model limit) by the SDK automatically.
    Raises openai.OpenAIError on failure (caller should catch and skip embedding).
    """
    client = _get_client()
    try:
        resp = await client.embeddings.create(
            model=settings.embedding_model,
            input=text,
            dimensions=settings.embedding_dimensions,
        )
        vector = resp.data[0].embedding
        tokens = resp.usage.prompt_tokens
        cost_micros, _ = calculate_cost_usd_micros(
            provider="openai",
            model=settings.embedding_model,
            prompt_tokens=tokens,
            completion_tokens=0,
        )
        logger.debug(
            "embedding.created",
            model=settings.embedding_model,
            tokens=tokens,
            dimensions=len(vector),
        )
        return vector, tokens, cost_micros
    except openai.OpenAIError as exc:
        logger.error("embedding.failed", error=str(exc))
        raise
