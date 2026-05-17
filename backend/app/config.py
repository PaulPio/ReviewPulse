from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    app_name: str = "ReviewPulse"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/reviewpulse"
    database_echo: bool = False

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Supabase Auth
    supabase_url: str = "http://localhost:54321"
    supabase_jwt_secret: str = "super-secret-jwt-token-with-at-least-32-characters"

    # OpenRouter LLM
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    llm_analysis_model: str = "google/gemini-2.0-flash-001"
    llm_embedding_model: str = "openai/text-embedding-3-small"

    # OpenAI fallback
    openai_api_key: str = ""

    # CORS
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Celery
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
