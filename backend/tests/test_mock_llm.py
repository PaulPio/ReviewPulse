from app.llm.mock import MockLLMClient
from app.llm.schemas import AnalysisResult


def test_mock_llm_returns_valid_analysis():
    c = MockLLMClient()
    text = "I loved the characters but the pacing dragged in the middle."
    result, usage = c.analyze_review(text, rating=4)
    assert isinstance(result, AnalysisResult)
    assert result.sentiment in ("positive", "mixed", "negative")
    assert 0 <= result.sentiment_confidence <= 1
    assert isinstance(result.themes, list)
    assert usage.prompt_tokens >= 0


def test_mock_embeddings_dimensions():
    c = MockLLMClient()
    vecs, usage = c.embed_texts(["hello", "world"])
    assert len(vecs) == 2
    assert len(vecs[0]) == 1536
