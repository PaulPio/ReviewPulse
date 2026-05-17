"""Webhook registration endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_author
from app.db.base import get_db
from app.models.author import Author
from app.models.webhook import WebhookDelivery

router = APIRouter()


@router.get("")
async def list_webhooks(
    current_author: Author = Depends(get_current_author),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(WebhookDelivery)
        .where(WebhookDelivery.author_id == current_author.id)
        .order_by(WebhookDelivery.created_at.desc())
        .limit(50)
    )
    deliveries = result.scalars().all()
    return {"data": [{"id": str(d.id), "event": d.event, "succeeded": d.succeeded, "created_at": d.created_at.isoformat()} for d in deliveries]}


@router.post("")
async def register_webhook(
    body: dict,
    current_author: Author = Depends(get_current_author),
):
    return {
        "data": {
            "message": "Webhook registration noted",
            "url": body.get("url"),
            "events": body.get("events", ["ingestion.completed"]),
        }
    }
