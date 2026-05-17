"""
Webhook delivery task (N10).

Payload format
--------------
{
  "event": "ingestion.completed",
  "job_id": "uuid",
  "author_id": "uuid",
  "status": "completed" | "partial" | "failed",
  "processed_reviews": int,
  "failed_reviews": int,
  "timestamp": "ISO-8601"
}

Signature
---------
The payload (JSON bytes) is signed with HMAC-SHA256 using `WEBHOOK_HMAC_SECRET`.
The signature is included in the payload AND in the `X-ReviewPulse-Signature` header.

Verification example (Python):
    import hashlib, hmac, json
    secret = b"your-webhook-hmac-secret"
    payload = b'{"event":"ingestion.completed",...}'
    expected = "sha256=" + hmac.new(secret, payload, hashlib.sha256).hexdigest()
    assert hmac.compare_digest(expected, request.headers["X-ReviewPulse-Signature"])

Retry policy
------------
Webhooks are retried up to 3 times with exponential backoff.
Failures are recorded in WebhookDelivery for audit purposes.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import sign_webhook_payload
from app.db.base import AsyncSessionLocal
from app.models.webhook import WebhookDelivery
from app.workers.celery_app import celery_app

logger = get_logger(__name__)

# Default webhook URL — authors can configure per-author URLs in a future iteration.
# For now we use a single global URL from settings (or skip if not configured).
WEBHOOK_TARGET_URL = ""  # populated from env: WEBHOOK_TARGET_URL


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    name="app.tasks.webhook.deliver_webhook",
)
def deliver_webhook(
    self,
    job_id: str,
    author_id: str,
    status: str,
    processed: int,
    failed: int,
    target_url: str | None = None,
) -> None:
    asyncio.run(
        _deliver(
            self,
            job_id=job_id,
            author_id=author_id,
            status=status,
            processed=processed,
            failed=failed,
            target_url=target_url,
        )
    )


async def _deliver(
    task,
    job_id: str,
    author_id: str,
    status: str,
    processed: int,
    failed: int,
    target_url: str | None,
) -> None:
    url = target_url or getattr(settings, "webhook_target_url", "")
    if not url:
        logger.debug("webhook.no_target_url", job_id=job_id)
        return

    payload = {
        "event": "ingestion.completed",
        "job_id": job_id,
        "author_id": author_id,
        "status": status,
        "processed_reviews": processed,
        "failed_reviews": failed,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode()
    signature = sign_webhook_payload(payload_bytes)

    attempt = task.request.retries + 1
    succeeded = False
    response_status: int | None = None
    response_body: str | None = None
    error: str | None = None

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                url,
                content=payload_bytes,
                headers={
                    "Content-Type": "application/json",
                    "X-ReviewPulse-Signature": signature,
                    "X-ReviewPulse-Event": "ingestion.completed",
                },
            )
            response_status = resp.status_code
            response_body = resp.text[:2000]
            resp.raise_for_status()
            succeeded = True
            logger.info(
                "webhook.delivered",
                job_id=job_id,
                url=url,
                status_code=resp.status_code,
                attempt=attempt,
            )
    except httpx.HTTPStatusError as exc:
        error = f"HTTP {exc.response.status_code}: {exc.response.text[:200]}"
        logger.warning("webhook.delivery_failed", job_id=job_id, error=error, attempt=attempt)
        task.retry(countdown=30 * (2 ** task.request.retries))
    except Exception as exc:
        error = str(exc)
        logger.warning("webhook.delivery_error", job_id=job_id, error=error, attempt=attempt)
        task.retry(countdown=30 * (2 ** task.request.retries))
    finally:
        # Always record delivery attempt
        async with AsyncSessionLocal() as db:
            delivery = WebhookDelivery(
                author_id=author_id,
                job_id=job_id,
                event="ingestion.completed",
                target_url=url,
                payload=payload,
                signature=signature,
                response_status=response_status,
                response_body=response_body,
                attempt_count=attempt,
                succeeded=succeeded,
                error=error,
            )
            db.add(delivery)
            await db.commit()
