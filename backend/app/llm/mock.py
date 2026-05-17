from __future__ import annotations

from app.llm.protocol import LLMClient
from app.llm.schemas import AnalysisResult, TokenUsage


class MockLLMClient:
    """Deterministic second implementation for tests (N2/N6)."""

    def analyze_review(self, review_text: str, rating: int | None) -> tuple[AnalysisResult, TokenUsage]:
        negative = any(w in review_text.lower() for w in ("terrible", "waste", "boring", "awful", "1 star"))
        pos = any(w in review_text.lower() for w in ("loved", "great", "excellent", "amazing", "five"))
        if negative and not pos:
            sentiment = "negative"
        elif pos and not negative:
            sentiment = "positive"
        else:
            sentiment = "mixed"
        themes = []
        if "pace" in review_text.lower() or "pacing" in review_text.lower():
            themes.append("pacing")
        if "character" in review_text.lower():
            themes.append("characters")
        if not themes:
            themes = ["general"]
        return AnalysisResult(
            sentiment=sentiment,
            sentiment_confidence=0.72,
            themes=themes,
            ai_generated=False,
            ai_generated_confidence=0.1,
            summary=(review_text[:120] + "…") if len(review_text) > 120 else review_text,
            actionable="?" in review_text or "why" in review_text.lower(),
        ), TokenUsage(
            prompt_tokens=400,
            completion_tokens=120,
            estimated_cost_usd=0.0001,
            model_id="mock/reviewpulse",
        )

    def embed_texts(self, texts: list[str]) -> tuple[list[list[float]], TokenUsage]:
        dim = 1536
        vectors = []
        for i, t in enumerate(texts):
            seed = sum(ord(c) for c in t[:200]) + i
            rng = seed % 997 / 997.0
            vec = [((seed + j * 13) % 1000) / 1000.0 * 0.1 + rng * 0.01 for j in range(dim)]
            vectors.append(vec)
        return vectors, TokenUsage(
            prompt_tokens=len(texts) * 10,
            completion_tokens=0,
            estimated_cost_usd=0.0,
            model_id="mock-embed/reviewpulse",
        )


def get_mock_llm_client() -> LLMClient:
    return MockLLMClient()
