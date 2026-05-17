"""
Import all models here so Alembic's autogenerate can discover them.
"""

from app.models.author import Author  # noqa: F401
from app.models.book import Book  # noqa: F401
from app.models.review import Review  # noqa: F401
from app.models.ingestion_job import IngestionJob  # noqa: F401
from app.models.llm_usage import LLMUsage  # noqa: F401
from app.models.webhook import WebhookDelivery  # noqa: F401
