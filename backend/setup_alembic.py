"""
Run this script once to create the alembic/ directory structure.

    python setup_alembic.py

This creates:
    alembic/
    alembic/env.py
    alembic/script.py.mako
    alembic/versions/
    alembic/versions/001_initial_schema.py
"""

import os
from pathlib import Path

BASE = Path(__file__).parent

ALEMBIC_DIR = BASE / "alembic"
VERSIONS_DIR = ALEMBIC_DIR / "versions"

ALEMBIC_DIR.mkdir(exist_ok=True)
VERSIONS_DIR.mkdir(exist_ok=True)

# ------------------------------------------------------------------ #
# env.py
# ------------------------------------------------------------------ #
(ALEMBIC_DIR / "env.py").write_text(
    '''"""
Alembic migration environment — async SQLAlchemy 2.0 setup.

The database URL is read from app.core.config.settings, so DATABASE_URL
in .env controls both the app and migrations.

All models are imported via app.models so autogenerate picks up every table.
Add new models to app/models/__init__.py.

Usage
-----
    cd backend
    alembic revision --autogenerate -m "description"
    alembic upgrade head
    alembic downgrade -1
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

import app.models  # noqa: F401 - registers all models with Base.metadata
from app.db.base import Base
from app.core.config import settings

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
'''
)

# ------------------------------------------------------------------ #
# script.py.mako
# ------------------------------------------------------------------ #
(ALEMBIC_DIR / "script.py.mako").write_text(
    '''"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from __future__ import annotations
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
'''
)

# ------------------------------------------------------------------ #
# versions/001_initial_schema.py
# ------------------------------------------------------------------ #
(VERSIONS_DIR / "001_initial_schema.py").write_text(
    '''"""Initial schema - all tables.

Revision ID: 001
Revises:
Create Date: 2026-05-17
"""

from __future__ import annotations
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "authors",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("hashed_password", sa.Text, nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("supabase_uid", sa.String(255), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_authors_email", "authors", ["email"], unique=True)

    op.create_table(
        "books",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("author_id", UUID(as_uuid=True), sa.ForeignKey("authors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("isbn", sa.String(20), nullable=True),
        sa.Column("asin", sa.String(20), nullable=True),
        sa.Column("amazon_url", sa.Text, nullable=True),
        sa.Column("cover_url", sa.Text, nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_books_author_id", "books", ["author_id"])
    op.create_index("ix_books_isbn", "books", ["isbn"])

    op.create_table(
        "reviews",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("book_id", UUID(as_uuid=True), sa.ForeignKey("books.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_id", UUID(as_uuid=True), sa.ForeignKey("authors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("external_id", sa.String(255), nullable=False),
        sa.Column("reviewer_name", sa.String(255), nullable=True),
        sa.Column("rating", sa.Integer, nullable=True),
        sa.Column("title", sa.String(512), nullable=True),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("review_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_purchase", sa.Boolean, default=False),
        sa.Column("source", sa.String(50), default="synthetic"),
        sa.Column("sentiment", sa.String(20), nullable=True),
        sa.Column("sentiment_confidence", sa.Float, nullable=True),
        sa.Column("themes", ARRAY(sa.String), nullable=True),
        sa.Column("is_ai_generated", sa.Boolean, nullable=True),
        sa.Column("ai_generated_confidence", sa.Float, nullable=True),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("is_actionable", sa.Boolean, nullable=True),
        sa.Column("actionable_reason", sa.Text, nullable=True),
        sa.Column("analysis_raw", JSONB, nullable=True),
        sa.Column("embedding", ARRAY(sa.Float), nullable=True),
        sa.Column("analyzed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("book_id", "external_id", name="uq_reviews_book_external"),
    )
    op.create_index("ix_reviews_book_id", "reviews", ["book_id"])
    op.create_index("ix_reviews_author_id", "reviews", ["author_id"])
    op.create_index("ix_reviews_review_date", "reviews", ["review_date"])
    op.create_index("ix_reviews_sentiment", "reviews", ["sentiment"])
    op.create_index("ix_reviews_is_ai_generated", "reviews", ["is_ai_generated"])
    op.create_index("ix_reviews_is_actionable", "reviews", ["is_actionable"])
    op.create_index("ix_reviews_created_at", "reviews", ["created_at"])

    op.create_table(
        "ingestion_jobs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("book_id", UUID(as_uuid=True), sa.ForeignKey("books.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_id", UUID(as_uuid=True), sa.ForeignKey("authors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, default="queued"),
        sa.Column("celery_task_id", sa.String(255), nullable=True),
        sa.Column("total_reviews", sa.Integer, default=0),
        sa.Column("processed_reviews", sa.Integer, default=0),
        sa.Column("failed_reviews", sa.Integer, default=0),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("error_details", JSONB, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_ingestion_jobs_book_id", "ingestion_jobs", ["book_id"])
    op.create_index("ix_ingestion_jobs_author_id", "ingestion_jobs", ["author_id"])
    op.create_index("ix_ingestion_jobs_status", "ingestion_jobs", ["status"])

    op.create_table(
        "llm_usage",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("author_id", UUID(as_uuid=True), sa.ForeignKey("authors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("book_id", UUID(as_uuid=True), sa.ForeignKey("books.id", ondelete="SET NULL"), nullable=True),
        sa.Column("review_id", UUID(as_uuid=True), sa.ForeignKey("reviews.id", ondelete="SET NULL"), nullable=True),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("operation", sa.String(100), nullable=False),
        sa.Column("prompt_tokens", sa.Integer, default=0),
        sa.Column("completion_tokens", sa.Integer, default=0),
        sa.Column("total_tokens", sa.Integer, default=0),
        sa.Column("cost_usd_micros", sa.BigInteger, default=0),
        sa.Column("pricing_snapshot", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_llm_usage_author_id", "llm_usage", ["author_id"])
    op.create_index("ix_llm_usage_book_id", "llm_usage", ["book_id"])
    op.create_index("ix_llm_usage_created_at", "llm_usage", ["created_at"])

    op.create_table(
        "webhook_deliveries",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("author_id", UUID(as_uuid=True), sa.ForeignKey("authors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_id", UUID(as_uuid=True), sa.ForeignKey("ingestion_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event", sa.String(100), nullable=False),
        sa.Column("target_url", sa.Text, nullable=False),
        sa.Column("payload", JSONB, nullable=False),
        sa.Column("signature", sa.String(80), nullable=False),
        sa.Column("response_status", sa.Integer, nullable=True),
        sa.Column("response_body", sa.Text, nullable=True),
        sa.Column("attempt_count", sa.Integer, default=1),
        sa.Column("succeeded", sa.Boolean, nullable=False, default=False),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_webhook_deliveries_author_id", "webhook_deliveries", ["author_id"])
    op.create_index("ix_webhook_deliveries_job_id", "webhook_deliveries", ["job_id"])

    # pgvector HNSW index for cosine similarity search
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_reviews_embedding_hnsw
        ON reviews
        USING hnsw ((embedding::vector(1536)) vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_reviews_embedding_hnsw")
    op.drop_table("webhook_deliveries")
    op.drop_table("llm_usage")
    op.drop_table("ingestion_jobs")
    op.drop_table("reviews")
    op.drop_table("books")
    op.drop_table("authors")
'''
)

print("alembic/ directory created successfully.")
print("Run: alembic upgrade head")
