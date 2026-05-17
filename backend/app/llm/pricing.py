"""Rough per-1M-token pricing for OpenRouter-backed models (USD). Fallback when API omits cost."""

from __future__ import annotations

from typing import ClassVar

MODEL_PRICE_PER_1M: dict[str, tuple[float, float]] = {
    # (input, output) per 1M tokens — approximate from public listings; override with measured API costs when present.
    "openai/gpt-4o-mini": (0.15, 0.60),
    "openai/gpt-4o": (2.5, 10.0),
    "google/gemini-2.0-flash-001": (0.10, 0.40),
    "openai/text-embedding-3-small": (0.02, 0.0),
}


def estimate_cost_usd(model_id: str, prompt_tokens: int, completion_tokens: int) -> float:
    key = next((k for k in MODEL_PRICE_PER_1M if k in model_id or model_id.startswith(k)), None)
    if key is None:
        key = model_id if model_id in MODEL_PRICE_PER_1M else None
    if key is None:
        parts = model_id.rsplit("/", 1)
        short = parts[-1] if parts else model_id
        key = short if short in MODEL_PRICE_PER_1M else "openai/gpt-4o-mini"
    inp, out = MODEL_PRICE_PER_1M.get(key, (0.15, 0.60))
    return (prompt_tokens / 1_000_000) * inp + (completion_tokens / 1_000_000) * out
