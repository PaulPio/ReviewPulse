from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.schemas import AuthorBootstrap, AuthorOut
from app.auth import decode_jwt_payload, parse_bearer
from app.config import get_settings
from app.dependencies import current_author, get_db_session
from app.models import Author

router = APIRouter(tags=["auth"])


@router.post("/auth/dev-authors", response_model=AuthorOut)
def dev_create_author(
    body: AuthorBootstrap,
    db: Session = Depends(get_db_session),
) -> Author:
    settings = get_settings()
    if not settings.dev_auth_bypass:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    author = Author(display_name=body.display_name)
    db.add(author)
    db.commit()
    db.refresh(author)
    return author


@router.post("/auth/bootstrap", response_model=AuthorOut)
def bootstrap_author(
    body: AuthorBootstrap,
    db: Session = Depends(get_db_session),
    authorization: Annotated[str | None, Header()] = None,
) -> Author:
    settings = get_settings()
    token = parse_bearer(authorization)
    if not token:
        if settings.dev_auth_bypass:
            raise HTTPException(
                status_code=401,
                detail="Missing bearer token; use POST /api/v1/auth/dev-authors for local dev",
            )
        raise HTTPException(status_code=401, detail="Missing bearer token")
    payload = decode_jwt_payload(token)
    sub = str(payload.get("sub", ""))
    existing = db.scalar(select(Author).where(Author.supabase_user_id == sub))
    if existing:
        if body.display_name and existing.display_name != body.display_name:
            existing.display_name = body.display_name
            db.add(existing)
            db.commit()
            db.refresh(existing)
        return existing
    author = Author(
        supabase_user_id=sub,
        email=str(payload.get("email")) if payload.get("email") else None,
        display_name=body.display_name,
    )
    db.add(author)
    db.commit()
    db.refresh(author)
    return author


@router.get("/auth/me", response_model=AuthorOut)
def me(author: Author = Depends(current_author)) -> Author:
    return author


@router.post("/session/ping")
def ping(author: Author = Depends(current_author), db: Session = Depends(get_db_session)) -> dict:
    author.last_seen_at = datetime.now(UTC)
    db.add(author)
    db.commit()
    return {"ok": True}
