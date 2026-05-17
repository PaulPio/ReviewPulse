"""job idempotency key for ingest"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "002_job_idempotency"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("idempotency_key", sa.String(length=128), nullable=True))
    op.create_unique_constraint(
        "uq_jobs_author_book_idempotency_key",
        "jobs",
        ["author_id", "book_id", "idempotency_key"],
    )
    op.create_index(op.f("ix_jobs_idempotency_key"), "jobs", ["idempotency_key"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_jobs_idempotency_key"), table_name="jobs")
    op.drop_constraint("uq_jobs_author_book_idempotency_key", "jobs", type_="unique")
    op.drop_column("jobs", "idempotency_key")
