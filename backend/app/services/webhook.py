import hashlib
import hmac
from typing import Any

import httpx
from fastapi import HTTPException, status

from app.config import get_settings
from app.logging_config import get_logger

log = get_logger("webhook")


def sign_body(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def verify_request_signature(header_value: str | None, body: bytes, secret: str) -> None:
    """Validate X-ReviewPulse-Signature: sha256=<hex> (constant-time compare)."""
    if not header_value or not header_value.startswith("sha256="):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid X-ReviewPulse-Signature",
        )
    got = header_value.removeprefix("sha256=")
    expected = sign_body(body, secret)
    if len(got) != len(expected) or not hmac.compare_digest(got, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")


def effective_ingestion_secret() -> str:
    s = get_settings()
    v = (s.webhook_ingestion_secret or s.webhook_signing_secret or "").strip()
    return v


def deliver_ingestion_webhook(payload: dict[str, Any]) -> None:
    settings = get_settings()
    url = (settings.webhook_delivery_url or "").strip()
    if not url:
        return
    import json

    body = json.dumps(payload, separators=(",", ":"), default=str).encode("utf-8")
    sig = sign_body(body, settings.webhook_signing_secret)
    headers = {
        "Content-Type": "application/json",
        "X-ReviewPulse-Signature": f"sha256={sig}",
    }
    try:
        r = httpx.post(url, content=body, headers=headers, timeout=10.0)
        r.raise_for_status()
        log.info("webhook_delivered", url=url, status_code=r.status_code)
    except Exception as e:
        log.warning("webhook_failed", url=url, error=str(e), exc_info=True)
