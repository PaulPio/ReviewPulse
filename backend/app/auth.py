from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import Header, HTTPException, status
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Author


def parse_bearer(authorization: str | None) -> str | None:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    return authorization.split(" ", 1)[1].strip()


def decode_jwt_payload(token: str) -> dict[str, Any]:
    settings = get_settings()
    if not settings.supabase_jwt_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SUPABASE_JWT_SECRET is not configured",
        )
    try:
        return jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except JWTError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from e


def get_author_for_request(
    db: Session,
    *,
    authorization: str | None,
    x_dev_author_id: str | None,
) -> tuple[Author, dict[str, Any]]:
    settings = get_settings()
    if settings.dev_auth_bypass and x_dev_author_id:
        try:
            aid = uuid.UUID(x_dev_author_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail="Invalid X-Dev-Author-Id") from e
        author = db.get(Author, aid)
        if author is None:
            raise HTTPException(status_code=401, detail="Unknown dev author id")
        return author, {"mode": "dev", "sub": str(aid)}

    token = parse_bearer(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing bearer token")
    payload = decode_jwt_payload(token)
    sub = str(payload.get("sub", ""))
    author = db.scalar(select(Author).where(Author.supabase_user_id == sub))
    if author is None:
        raise HTTPException(status_code=401, detail="Author not registered; call POST /api/v1/auth/bootstrap")
    return author, payload


def touch_last_seen(db: Session, author: Author) -> None:
    now = datetime.now(UTC)
    if author.last_seen_at and (now - author.last_seen_at).total_seconds() < 60:
        return
    author.last_seen_at = now
    db.add(author)
    db.commit()
    db.refresh(author)
