"""Shared FastAPI dependencies: auth, DB session."""

from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.base import get_db
from app.models.author import Author

_bearer = HTTPBearer(auto_error=False)


async def get_current_author(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> Author:
    """Decode JWT, upsert author row, return Author instance."""
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        payload = decode_access_token(credentials.credentials)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    author_id = payload.get("sub")
    if not author_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    result = await db.execute(select(Author).where(Author.id == uuid.UUID(author_id)))
    author = result.scalar_one_or_none()

    if not author:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Author not found")

    return author
