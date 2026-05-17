"""Auth endpoints: register, login, me."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password, verify_password
from app.db.base import get_db
from app.models.author import Author
from app.schemas.author import AuthorRegister, AuthorLogin, AuthorOut, TokenOut
from app.api.deps import get_current_author

router = APIRouter()


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
async def register(data: AuthorRegister, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Author).where(Author.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    author = Author(
        id=uuid.uuid4(),
        email=data.email,
        display_name=data.display_name,
        hashed_password=hash_password(data.password),
        last_login_at=datetime.now(timezone.utc),
    )
    db.add(author)
    await db.flush()
    await db.refresh(author)

    token = create_access_token(str(author.id))
    return TokenOut(access_token=token, author=AuthorOut.model_validate(author))


@router.post("/login", response_model=TokenOut)
async def login(data: AuthorLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Author).where(Author.email == data.email))
    author = result.scalar_one_or_none()

    if not author or not verify_password(data.password, author.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    author.last_login_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(author)

    token = create_access_token(str(author.id))
    return TokenOut(access_token=token, author=AuthorOut.model_validate(author))


@router.get("/me", response_model=AuthorOut)
async def me(current_author: Author = Depends(get_current_author)):
    return AuthorOut.model_validate(current_author)
