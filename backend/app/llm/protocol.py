from typing import Protocol, runtime_checkable

from app.llm.schemas import AnalysisResult, TokenUsage


@runtime_checkable
class LLMClient(Protocol):
    def analyze_review(self, review_text: str, rating: int | None) -> tuple[AnalysisResult, TokenUsage]:
        """Return structured analysis and token usage for billing."""

    def embed_texts(self, texts: list[str]) -> tuple[list[list[float]], TokenUsage]:
        """Return embedding vectors (same order as input) and usage."""
