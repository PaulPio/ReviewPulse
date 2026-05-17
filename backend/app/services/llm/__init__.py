"""
LLM adapter layer — provider-agnostic interface with two implementations.

Design (N2)
-----------
`BaseLLMClient` defines the contract. `AnthropicClient` and `OpenAIClient`
implement it. `GeminiClient` provides the third. `get_llm_client()` is the
factory used everywhere else in the codebase — swap providers by changing
LLM_PROVIDER in .env with zero code changes.

Retry policy (N5)
-----------------
Each `complete()` call is wrapped with tenacity:
  - max_attempts: settings.llm_max_retries (default 3)
  - wait: exponential backoff between settings.llm_retry_min_wait and
          settings.llm_retry_max_wait
  - retry on: rate-limit / 5xx / network errors
  - failure mode: after all retries exhausted, raises `LLMError` which
                  the Celery task catches and marks the review as failed
                  (not the whole job), so partial success is preserved.
"""

from app.services.llm.base import BaseLLMClient, LLMError, LLMResponse  # noqa: F401
from app.services.llm.anthropic_client import AnthropicClient  # noqa: F401
from app.services.llm.openai_client import OpenAIClient  # noqa: F401
from app.services.llm.gemini_client import GeminiClient  # noqa: F401
from app.services.llm.factory import get_llm_client  # noqa: F401
