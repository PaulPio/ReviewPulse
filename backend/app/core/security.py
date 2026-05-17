"""
Security utilities: JWT creation/verification, password hashing, HMAC webhook signing.

JWT strategy
------------
We issue HS256 JWTs ourselves. Each token carries:
  - sub  : author UUID (str)
  - exp  : expiry timestamp
  - type : "access"

The token is verified on every protected request via the `get_current_author`
dependency in app/api/deps.py.

Webhook HMAC
------------
Payloads are signed with HMAC-SHA256 using `settings.webhook_hmac_secret`.
The signature is sent in the `X-ReviewPulse-Signature` header as
`sha256=<hex_digest>`.

Verification example (curl):
    PAYLOAD='{"event":"ingestion.completed","job_id":"..."}'
    SECRET='your-webhook-hmac-secret'
    SIG=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$SECRET" | awk '{print $2}')
    # Compare $SIG with header value after stripping "sha256=" prefix
"""

from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# ------------------------------------------------------------------ #
# Password hashing
# ------------------------------------------------------------------ #
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


# ------------------------------------------------------------------ #
# JWT
# ------------------------------------------------------------------ #
def create_access_token(subject: str | UUID, expires_delta: timedelta | None = None) -> str:
    """Create a signed JWT access token for *subject* (author UUID)."""
    now = datetime.now(timezone.utc)
    expire = now + (
        expires_delta
        or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload: dict[str, Any] = {
        "sub": str(subject),
        "exp": expire,
        "iat": now,
        "type": "access",
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT.

    Raises `jose.JWTError` on invalid / expired tokens — callers should
    catch this and raise HTTP 401.
    """
    return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])


# ------------------------------------------------------------------ #
# Webhook HMAC signing
# ------------------------------------------------------------------ #
def sign_webhook_payload(payload_bytes: bytes) -> str:
    """Return `sha256=<hex>` signature for a raw payload."""
    digest = hmac.new(
        settings.webhook_hmac_secret.encode(),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()
    return f"sha256={digest}"


def verify_webhook_signature(payload_bytes: bytes, signature_header: str) -> bool:
    """
    Constant-time comparison of the expected HMAC against the received header.

    The header value must be in the form `sha256=<hex_digest>`.
    Returns True if valid, False otherwise.
    """
    expected = sign_webhook_payload(payload_bytes)
    return hmac.compare_digest(expected.encode(), signature_header.encode())
