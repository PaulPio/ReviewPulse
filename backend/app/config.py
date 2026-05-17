from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+psycopg://reviewpulse:reviewpulse@localhost:5433/reviewpulse"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"

    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_referer: str = ""
    openrouter_app_name: str = "ReviewPulse"
    openrouter_model_analysis: str = "openai/gpt-4o-mini"
    openrouter_model_embedding: str = "openai/text-embedding-3-small"
    embedding_dimensions: int = 1536

    supabase_jwt_secret: str = ""
    dev_auth_bypass: bool = False

    webhook_signing_secret: str = "dev-webhook-secret"
    webhook_ingestion_secret: str = ""  # falls back to webhook_signing_secret if empty
    webhook_delivery_url: str = ""

    log_level: str = "INFO"

    sample_reviews_path: str = ""  # default resolved in code relative to package


@lru_cache
def get_settings() -> Settings:
    return Settings()
