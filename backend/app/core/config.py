"""
Application configuration via Pydantic Settings.
All settings are read from environment variables (or a .env file).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
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
    # Comma-separated list of allowed origins for CORS
    cors_origins: list[AnyHttpUrl] = Field(default_factory=list)

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
    # Embedding model for pgvector (tiktoken-compatible)
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

    # ------------------------------------------------------------------ #
    # Validators
    # ------------------------------------------------------------------ #
    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors(cls, v: str | list) -> list:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings singleton."""
    return Settings()


settings = get_settings()
