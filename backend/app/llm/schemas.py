from typing import Literal

from pydantic import BaseModel, Field


class AnalysisResult(BaseModel):
    sentiment: Literal["positive", "mixed", "negative"]
    sentiment_confidence: float = Field(ge=0, le=1)
    themes: list[str] = Field(default_factory=list)
    ai_generated: bool
    ai_generated_confidence: float = Field(ge=0, le=1)
    summary: str
    actionable: bool


class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    estimated_cost_usd: float = 0.0
    model_id: str = ""
