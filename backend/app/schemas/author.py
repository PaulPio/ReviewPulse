"""Pydantic v2 schemas for Author / Auth endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class AuthorRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=255)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if v.isdigit() or v.isalpha():
            raise ValueError("Password must contain letters and numbers")
        return v


class AuthorLogin(BaseModel):
    email: EmailStr
    password: str


class AuthorOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    email: str
    display_name: str
    last_login_at: datetime | None
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    author: AuthorOut


class AuthorUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=255)
