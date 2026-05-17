"""Pydantic v2 schemas for IngestionJob endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, computed_field


JobStatus = Literal["queued", "running", "completed", "failed", "partial"]


class JobTriggerRequest(BaseModel):
    """Optional body when triggering an ingestion job."""
    force_reanalyze: bool = False  # reprocess already-analyzed reviews


class JobOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    book_id: uuid.UUID
    author_id: uuid.UUID
    status: JobStatus
    celery_task_id: str | None
    total_reviews: int
    processed_reviews: int
    failed_reviews: int
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime

    @computed_field
    @property
    def progress_pct(self) -> float:
        """Progress 0-100. Exposed in JSON for polling UIs."""
        if self.total_reviews == 0:
            return 0.0
        return round(self.processed_reviews / self.total_reviews * 100, 1)
