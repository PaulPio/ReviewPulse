from __future__ import annotations

import json
import random
import time

from openai import APIError, OpenAI, RateLimitError
from pydantic import ValidationError

from app.config import Settings, get_settings
from app.llm.pricing import estimate_cost_usd
from app.llm.protocol import LLMClient
from app.llm.schemas import AnalysisResult, TokenUsage


class OpenRouterClient:
    """OpenAI-compatible client pointed at OpenRouter."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        headers = {}
        if self.settings.openrouter_referer:
            headers["HTTP-Referer"] = self.settings.openrouter_referer
        if self.settings.openrouter_app_name:
            headers["X-Title"] = self.settings.openrouter_app_name
        self._client = OpenAI(
            base_url=self.settings.openrouter_base_url,
            api_key=self.settings.openrouter_api_key or "missing",
            default_headers=headers or None,
        )

    def _with_retries(self, fn, *, max_attempts: int = 5, label: str = "openrouter"):
        delay = 0.5
        last_exc: Exception | None = None
        for attempt in range(1, max_attempts + 1):
            try:
                return fn()
            except RateLimitError as e:
                last_exc = e
            except APIError as e:
                if getattr(e, "status_code", None) in (429, 500, 502, 503, 504):
                    last_exc = e
                else:
                    raise
            sleep = delay * (2 ** (attempt - 1)) + random.random() * 0.2
            time.sleep(min(sleep, 30.0))
        assert last_exc
        raise last_exc

    def analyze_review(self, review_text: str, rating: int | None) -> tuple[AnalysisResult, TokenUsage]:
        model = self.settings.openrouter_model_analysis
        rating_line = f"Star rating (1-5): {rating}\n" if rating is not None else ""
        system = (
            "You are a publishing assistant. Respond with a single JSON object only, no markdown. "
            "Schema keys: sentiment (one of positive|mixed|negative), sentiment_confidence (0-1), "
            "themes (array of short strings like pacing, characters), "
            "ai_generated (boolean), ai_generated_confidence (0-1), summary (one sentence), "
            "actionable (boolean: author could respond or fix in a future edition)."
        )
        user = f"{rating_line}Review text:\n{review_text}"

        def call():
            return self._client.chat.completions.create(
                model=model,
                temperature=0.2,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )

        resp = self._with_retries(call, label="analyze")
        content = resp.choices[0].message.content or "{}"

        def parse_and_validate(text: str) -> AnalysisResult:
            data = json.loads(text)
            return AnalysisResult.model_validate(data)

        try:
            result = parse_and_validate(content)
        except (json.JSONDecodeError, ValidationError):

            def repair():
                return self._client.chat.completions.create(
                    model=model,
                    temperature=0,
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                        {
                            "role": "user",
                            "content": (
                                "The previous assistant reply was not valid JSON matching the schema. "
                                "Reply again with ONLY a single JSON object using the same keys as specified."
                            ),
                        },
                    ],
                )

            resp2 = self._with_retries(repair, label="analyze_json_repair")
            content2 = resp2.choices[0].message.content or "{}"
            result = parse_and_validate(content2)
            usage = resp.usage
            u2 = resp2.usage
            pt = (usage.prompt_tokens if usage else 0) + (u2.prompt_tokens if u2 else 0)
            ct = (usage.completion_tokens if usage else 0) + (u2.completion_tokens if u2 else 0)
            cost = getattr(usage, "total_cost", None) if usage else None
            if cost is None and usage and hasattr(usage, "model_extra"):
                cost = usage.model_extra.get("total_cost") if usage.model_extra else None
            cost2 = getattr(u2, "total_cost", None) if u2 else None
            if cost2 is None and u2 and hasattr(u2, "model_extra"):
                cost2 = u2.model_extra.get("total_cost") if u2.model_extra else None
            api_cost = None
            if cost is not None or cost2 is not None:
                api_cost = float(cost or 0) + float(cost2 or 0)
            est = (
                float(api_cost)
                if api_cost is not None
                else estimate_cost_usd(model, pt, ct)
            )
            token_usage = TokenUsage(
                prompt_tokens=pt,
                completion_tokens=ct,
                estimated_cost_usd=est,
                model_id=model,
            )
            return result, token_usage

        usage = resp.usage
        pt = usage.prompt_tokens if usage else 0
        ct = usage.completion_tokens if usage else 0
        cost = getattr(usage, "total_cost", None) if usage else None
        if cost is None and usage and hasattr(usage, "model_extra"):
            cost = usage.model_extra.get("total_cost") if usage.model_extra else None
        est = float(cost) if cost is not None else estimate_cost_usd(model, pt, ct)
        token_usage = TokenUsage(
            prompt_tokens=pt,
            completion_tokens=ct,
            estimated_cost_usd=est,
            model_id=model,
        )
        return result, token_usage

    def embed_texts(self, texts: list[str]) -> tuple[list[list[float]], TokenUsage]:
        model = self.settings.openrouter_model_embedding

        def call():
            return self._client.embeddings.create(model=model, input=texts)

        resp = self._with_retries(call, label="embed")
        vectors = [d.embedding for d in sorted(resp.data, key=lambda x: x.index)]
        usage = resp.usage
        pt = usage.prompt_tokens if usage else 0
        est = estimate_cost_usd(model, pt, 0)
        token_usage = TokenUsage(
            prompt_tokens=pt,
            completion_tokens=0,
            estimated_cost_usd=est,
            model_id=model,
        )
        return vectors, token_usage


# Type-checker sees structural subtyping to LLMClient
def get_openrouter_client() -> LLMClient:
    return OpenRouterClient()
