"""
Application configuration via Pydantic Settings.
All settings are read from environment variables (or a .env file).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field, TypeAdapter, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _strip_trailing_dotenv_comment(value: object) -> object:
    """Strip accidental `VAR=x # doc` tails from merged .env values."""
    if isinstance(value, str) and " #" in value:
        return value.split(" #", 1)[0].strip()
    return value


def _normalize_browser_origin(url: AnyHttpUrl) -> str:
    """Browsers send `Origin` without a trailing slash; CORS match is exact."""
    return str(url).rstrip("/")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        # Empty env vars (e.g. CORS_ORIGINS=) skip JSON decoding for typed list fields elsewhere
        env_ignore_empty=True,
    )

    # ------------------------------------------------------------------ #
    # Application
    # ------------------------------------------------------------------ #
    app_name: str = "ReviewPulse"
    app_version: str = "0.1.0"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False

    # ------------------------------------------------------------------ #
    # API
    # ------------------------------------------------------------------ #
    api_v1_prefix: str = "/api/v1"
    # Read as plain string — pydantic-settings JSON-decodes list fields from .env otherwise.
    cors_origins_raw: str = Field(default="", validation_alias="CORS_ORIGINS")

    # ------------------------------------------------------------------ #
    # Database
    # ------------------------------------------------------------------ #
    # Full async DSN, e.g. postgresql+asyncpg://user:pass@host:5432/db
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/reviewpulse"
    )

    # Supabase (used for auth + optional direct DB access)
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""

    # ------------------------------------------------------------------ #
    # Redis / Celery
    # ------------------------------------------------------------------ #
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # ------------------------------------------------------------------ #
    # Auth / Security
    # ------------------------------------------------------------------ #
    secret_key: str = Field(
        default="change-me-in-production-generate-with-openssl-rand-hex-32"
    )
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24 hours

    # HMAC secret for webhook payloads
    webhook_hmac_secret: str = Field(
        default="change-me-webhook-hmac-secret"
    )

    # ------------------------------------------------------------------ #
    # LLM Providers
    # ------------------------------------------------------------------ #
    # Primary provider: "anthropic" | "openai" | "gemini" | "openrouter"
    llm_provider: Literal["anthropic", "openai", "gemini", "openrouter"] = "anthropic"
    llm_fallback_provider: Literal["anthropic", "openai", "gemini", "openrouter"] | None = "openai"

    anthropic_api_key: str = ""
    openai_api_key: str = ""
    gemini_api_key: str = ""
    openrouter_api_key: str = ""

    # Model names per provider
    anthropic_model: str = "claude-3-5-haiku-20241022"
    openai_model: str = "gpt-4o-mini"
    gemini_model: str = "gemini-1.5-flash"
    # Any model slug supported by OpenRouter, e.g. "google/gemini-2.0-flash-001"
    openrouter_model: str = "google/gemini-2.0-flash-001"

    # LLM retry policy
    llm_max_retries: int = 3
    llm_retry_min_wait: float = 1.0   # seconds
    llm_retry_max_wait: float = 60.0  # seconds

    # ------------------------------------------------------------------ #
    # Ingestion
    # ------------------------------------------------------------------ #
    # Max reviews to generate per book in synthetic mode
    synthetic_reviews_per_book: int = 50
    # Embedding provider: "openai" (direct) or "openrouter" (via gateway)
    embedding_provider: Literal["openai", "openrouter"] = "openai"
    # Model slug — for OpenRouter prefix with "openai/", e.g. "openai/text-embedding-3-small"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    # ------------------------------------------------------------------ #
    # Celery Beat schedule
    # ------------------------------------------------------------------ #
    # How often (in seconds) to refresh each book's reviews
    refresh_interval_seconds: int = 3600  # 1 hour

    # ------------------------------------------------------------------ #
    # Observability
    # ------------------------------------------------------------------ #
    log_level: str = "INFO"
    sentry_dsn: str = ""

    @field_validator("environment", "debug", mode="before")
    @classmethod
    def strip_inline_comments_env_flags(cls, v: object) -> object:
        return _strip_trailing_dotenv_comment(v)

    @field_validator("llm_provider", mode="before")
    @classmethod
    def strip_inline_comments_llm_primary(cls, v: object) -> object:
        return _strip_trailing_dotenv_comment(v)

    @field_validator("llm_fallback_provider", mode="before")
    @classmethod
    def coerce_llm_fallback_from_env(cls, v: object) -> object:
        """Mis-copied `.env` lines sometimes put `# ...` inside the variable value."""
        if not isinstance(v, str):
            return v
        s = _strip_trailing_dotenv_comment(v)
        if not isinstance(s, str):
            return s
        s = s.strip()
        if not s or s.startswith("#"):
            return None
        return s

    @field_validator("database_url", mode="before")
    @classmethod
    def coerce_async_database_url(cls, v: object) -> object:
        """
        Hosted Postgres URLs are often pasted as postgresql://… — SQLAlchemy async
        needs postgresql+asyncpg:// or startup/import fails for the async engine.
        """
        if not isinstance(v, str):
            return v
        v = _strip_trailing_dotenv_comment(v)
        if not isinstance(v, str):
            return v
        url = v.strip()
        if "://" not in url:
            return url
        scheme, _, remainder = url.partition("://")
        if "+" in scheme:
            return url
        base = scheme.lower()
        if base == "postgres":
            base = "postgresql"
        if base == "postgresql":
            return f"postgresql+asyncpg://{remainder}"
        return url

    # ------------------------------------------------------------------ #
    # Derived
    # ------------------------------------------------------------------ #
    @computed_field
    @property
    def cors_origins(self) -> list[str]:
        raw = self.cors_origins_raw.strip()
        if not raw:
            return []
        if raw.startswith("["):
            parsed = TypeAdapter(list[AnyHttpUrl]).validate_json(raw)
        else:
            parts = [o.strip() for o in raw.split(",") if o.strip()]
            parsed = TypeAdapter(list[AnyHttpUrl]).validate_python(parts)
        return [_normalize_browser_origin(u) for u in parsed]


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings singleton."""
    return Settings()


settings = get_settings()
