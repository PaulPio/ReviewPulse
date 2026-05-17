"""
Abstract base class and shared types for all LLM clients.

Token pricing (N3)
------------------
PRICING maps provider → model → {input, output} cost per 1K tokens in USD.
Prices are correct as of May 2026; update when providers reprice.
Cost is always recorded against LLMUsage so the dashboard can surface it.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


# USD per 1,000 tokens
PRICING: dict[str, dict[str, dict[str, float]]] = {
    "anthropic": {
        "claude-3-5-haiku-20241022": {"input": 0.0008, "output": 0.004},
        "claude-3-5-sonnet-20241022": {"input": 0.003, "output": 0.015},
    },
    "openai": {
        "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
        "gpt-4o": {"input": 0.0025, "output": 0.01},
        "text-embedding-3-small": {"input": 0.00002, "output": 0.0},
    },
    "gemini": {
        "gemini-1.5-flash": {"input": 0.000075, "output": 0.0003},
        "gemini-1.5-pro": {"input": 0.00125, "output": 0.005},
    },
}


def calculate_cost_usd_micros(
    provider: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> tuple[int, dict]:
    """
    Return (cost_in_usd_micros, pricing_snapshot).

    usd_micros = USD * 1_000_000 (integer math, no float drift).
    Returns (0, {}) if the model is not in PRICING.
    """
    model_pricing = PRICING.get(provider, {}).get(model, {})
    if not model_pricing:
        return 0, {}

    input_cost = (prompt_tokens / 1000) * model_pricing["input"]
    output_cost = (completion_tokens / 1000) * model_pricing["output"]
    total_usd = input_cost + output_cost
    return int(total_usd * 1_000_000), model_pricing


@dataclass
class LLMResponse:
    content: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    model: str
    provider: str
    raw: Any = field(default=None, repr=False)


class LLMError(Exception):
    """Raised when all retry attempts for an LLM call are exhausted."""

    def __init__(self, message: str, provider: str, cause: Exception | None = None):
        super().__init__(message)
        self.provider = provider
        self.cause = cause


class BaseLLMClient(ABC):
    """
    Provider-agnostic LLM interface.

    All implementations must support structured JSON output via
    `complete_json()` which calls `complete()` and parses the result.
    """

    provider: str = ""
    model: str = ""

    @abstractmethod
    async def complete(self, prompt: str, system: str = "") -> LLMResponse:
        """Send a completion request and return a structured response."""
        ...

    async def complete_json(self, prompt: str, system: str = "") -> tuple[dict, LLMResponse]:
        """
        Complete and parse JSON from the response.

        The model is instructed (in the system prompt) to return only valid JSON.
        We strip markdown fences if the model wraps output.
        """
        import json

        resp = await self.complete(prompt=prompt, system=system)
        text = resp.content.strip()

        # Strip markdown code fences
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise LLMError(
                f"Failed to parse JSON from {self.provider} response: {exc}",
                provider=self.provider,
                cause=exc,
            )
        return data, resp
