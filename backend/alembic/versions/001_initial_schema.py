"""Initial schema — all tables.

Revision ID: 001
Revises:
Create Date: 2026-05-17

This migration:
1. Creates the pgvector extension (requires Supabase/PostgreSQL with vector extension)
2. Creates all application tables in dependency order
3. Adds indexes for all common filter/sort columns

pgvector note
-------------
`CREATE EXTENSION IF NOT EXISTS vector` is idempotent and safe to run on
every migration run. Supabase enables it with one click in the dashboard.
On plain PostgreSQL: run `sudo apt install postgresql-16-pgvector` first.

The embedding column uses ARRAY(FLOAT) and is cast to ::vector in queries.
This avoids the pgvector ORM type dependency while remaining fully compatible
with pgvector cosine similarity operators.
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
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # authors
    op.create_table(
        "authors",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("hashed_password", sa.Text, nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("supabase_uid", sa.String(255), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_authors_email", "authors", ["email"], unique=True)
    op.create_index("uq_authors_supabase_uid", "authors", ["supabase_uid"], unique=True)

    # books
    op.create_table(
        "books",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "author_id",
            UUID(as_uuid=True),
            sa.ForeignKey("authors.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("isbn", sa.String(20), nullable=True),
        sa.Column("asin", sa.String(20), nullable=True),
        sa.Column("amazon_url", sa.Text, nullable=True),
        sa.Column("cover_url", sa.Text, nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_books_author_id", "books", ["author_id"])
    op.create_index("ix_books_isbn", "books", ["isbn"])
    op.create_index("ix_books_asin", "books", ["asin"])

    # reviews
    op.create_table(
        "reviews",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "book_id",
            UUID(as_uuid=True),
            sa.ForeignKey("books.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "author_id",
            UUID(as_uuid=True),
            sa.ForeignKey("authors.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("external_id", sa.String(255), nullable=False),
        sa.Column("reviewer_name", sa.String(255), nullable=True),
        sa.Column("rating", sa.Integer, nullable=True),
        sa.Column("title", sa.String(512), nullable=True),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("review_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_purchase", sa.Boolean, default=False),
        sa.Column("source", sa.String(50), default="synthetic"),
        # Analysis fields
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
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        # Idempotency constraint
        sa.UniqueConstraint("book_id", "external_id", name="uq_reviews_book_external"),
    )
    op.create_index("ix_reviews_book_id", "reviews", ["book_id"])
    op.create_index("ix_reviews_author_id", "reviews", ["author_id"])
    op.create_index("ix_reviews_review_date", "reviews", ["review_date"])
    op.create_index("ix_reviews_sentiment", "reviews", ["sentiment"])
    op.create_index("ix_reviews_is_ai_generated", "reviews", ["is_ai_generated"])
    op.create_index("ix_reviews_is_actionable", "reviews", ["is_actionable"])
    op.create_index("ix_reviews_created_at", "reviews", ["created_at"])

    # ingestion_jobs
    op.create_table(
        "ingestion_jobs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "book_id",
            UUID(as_uuid=True),
            sa.ForeignKey("books.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "author_id",
            UUID(as_uuid=True),
            sa.ForeignKey("authors.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(20), nullable=False, default="queued"),
        sa.Column("celery_task_id", sa.String(255), nullable=True),
        sa.Column("total_reviews", sa.Integer, default=0),
        sa.Column("processed_reviews", sa.Integer, default=0),
        sa.Column("failed_reviews", sa.Integer, default=0),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("error_details", JSONB, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_ingestion_jobs_book_id", "ingestion_jobs", ["book_id"])
    op.create_index("ix_ingestion_jobs_author_id", "ingestion_jobs", ["author_id"])
    op.create_index("ix_ingestion_jobs_status", "ingestion_jobs", ["status"])
    op.create_index("ix_ingestion_jobs_celery_task_id", "ingestion_jobs", ["celery_task_id"])

    # llm_usage
    op.create_table(
        "llm_usage",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "author_id",
            UUID(as_uuid=True),
            sa.ForeignKey("authors.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "book_id",
            UUID(as_uuid=True),
            sa.ForeignKey("books.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "review_id",
            UUID(as_uuid=True),
            sa.ForeignKey("reviews.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("operation", sa.String(100), nullable=False),
        sa.Column("prompt_tokens", sa.Integer, default=0),
        sa.Column("completion_tokens", sa.Integer, default=0),
        sa.Column("total_tokens", sa.Integer, default=0),
        sa.Column("cost_usd_micros", sa.BigInteger, default=0),
        sa.Column("pricing_snapshot", JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_llm_usage_author_id", "llm_usage", ["author_id"])
    op.create_index("ix_llm_usage_book_id", "llm_usage", ["book_id"])
    op.create_index("ix_llm_usage_created_at", "llm_usage", ["created_at"])

    # webhook_deliveries
    op.create_table(
        "webhook_deliveries",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "author_id",
            UUID(as_uuid=True),
            sa.ForeignKey("authors.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "job_id",
            UUID(as_uuid=True),
            sa.ForeignKey("ingestion_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event", sa.String(100), nullable=False),
        sa.Column("target_url", sa.Text, nullable=False),
        sa.Column("payload", JSONB, nullable=False),
        sa.Column("signature", sa.String(80), nullable=False),
        sa.Column("response_status", sa.Integer, nullable=True),
        sa.Column("response_body", sa.Text, nullable=True),
        sa.Column("attempt_count", sa.Integer, default=1),
        sa.Column("succeeded", sa.Boolean, nullable=False, default=False),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_webhook_deliveries_author_id", "webhook_deliveries", ["author_id"])
    op.create_index("ix_webhook_deliveries_job_id", "webhook_deliveries", ["job_id"])

    # Create pgvector index on reviews.embedding for fast cosine similarity search
    # HNSW index is more efficient than IVFFlat for small datasets (< 1M vectors)
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
