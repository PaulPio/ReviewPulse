"""Embedding generation service using OpenRouter or OpenAI."""

from __future__ import annotations

import httpx
import structlog

from app.core.config import settings

logger = structlog.get_logger()


async def generate_embedding(text: str) -> list[float] | None:
    """Generate a 1536-dim embedding for the given text."""
    if not settings.openai_api_key and not settings.anthropic_api_key:
        logger.warning("No API key configured for embeddings")
        return None

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                json={
                    "model": settings.embedding_model,
                    "input": text[:8000],
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["data"][0]["embedding"]
    except Exception as e:
        logger.error("embedding_generation_failed", error=str(e))
        return None


async def generate_embeddings_batch(texts: list[str]) -> list[list[float] | None]:
    """Generate embeddings for a batch of texts."""
    results = []
    for text in texts:
        emb = await generate_embedding(text)
        results.append(emb)
    return results
