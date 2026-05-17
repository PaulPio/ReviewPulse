from typing import Annotated, Any

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.auth import get_author_for_request
from app.db import get_db
from app.models import Author


def get_db_session():
    yield from get_db()


def current_author(
    db: Annotated[Session, Depends(get_db_session)],
    authorization: Annotated[str | None, Header()] = None,
    x_dev_author_id: Annotated[str | None, Header()] = None,
) -> Author:
    author, _payload = get_author_for_request(
        db, authorization=authorization, x_dev_author_id=x_dev_author_id
    )
    return author


def current_author_meta(
    db: Annotated[Session, Depends(get_db_session)],
    authorization: Annotated[str | None, Header()] = None,
    x_dev_author_id: Annotated[str | None, Header()] = None,
) -> tuple[Author, dict[str, Any]]:
    return get_author_for_request(
        db, authorization=authorization, x_dev_author_id=x_dev_author_id
    )
