import os
import re

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine.url import make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

os.environ["DEV_AUTH_BYPASS"] = "true"
os.environ["USE_MOCK_LLM"] = "1"
os.environ["SUPABASE_JWT_SECRET"] = "test-secret-for-jwt"
os.environ["WEBHOOK_SIGNING_SECRET"] = "test-webhook-secret"

from app.config import get_settings

get_settings.cache_clear()

from app.main import app
from app.models import Author, Base

_DB_NAME_SAFE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
_DEFAULT_TEST_URL = (
    "postgresql+psycopg://reviewpulse:reviewpulse@127.0.0.1:5433/reviewpulse_test"
)


def _ensure_test_database(dsn: str) -> None:
    url = make_url(dsn)
    if not url.database:
        raise ValueError("TEST_DATABASE_URL must include a database name")
    test_db = url.database
    if not _DB_NAME_SAFE.fullmatch(test_db):
        raise ValueError(f"Refusing non-alphanumeric test database name: {test_db!r}")

    admin_url = url.set(database="postgres")
    admin_eng = create_engine(
        admin_url,
        isolation_level="AUTOCOMMIT",
        connect_args={"connect_timeout": 10},
    )
    with admin_eng.connect() as c:
        row = c.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": test_db},
        ).first()
        if row is None:
            c.execute(text(f"CREATE DATABASE {test_db}"))


def _skip_postgres(reason: str, cause: Exception) -> None:
    pytest.skip(
        reason
        + " Start Postgres: docker compose up -d. "
        + f"Detail: {type(cause).__name__}: {cause}"
    )


@pytest.fixture(scope="session")
def engine():
    url = os.environ.get("TEST_DATABASE_URL", _DEFAULT_TEST_URL)
    try:
        _ensure_test_database(url)
    except OperationalError as e:
        _skip_postgres("Cannot reach Postgres to prepare the test database.", e)

    eng = create_engine(url, connect_args={"connect_timeout": 10})
    try:
        with eng.connect() as c:
            c.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            c.commit()
    except OperationalError as e:
        eng.dispose()
        _skip_postgres("Cannot create pgvector extension on test database.", e)

    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)


@pytest.fixture()
def db_session(engine) -> Session:
    SessionTesting = sessionmaker(bind=engine, expire_on_commit=False)
    s = SessionTesting()
    try:
        yield s
    finally:
        s.close()


@pytest.fixture()
def client(db_session: Session):
    from app.db import get_db
    from app.dependencies import get_db_session

    def _override():
        yield db_session

    app.dependency_overrides[get_db] = _override
    app.dependency_overrides[get_db_session] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def author_a(db_session: Session) -> Author:
    a = Author(display_name="Author A")
    db_session.add(a)
    db_session.commit()
    db_session.refresh(a)
    return a


@pytest.fixture()
def author_b(db_session: Session) -> Author:
    a = Author(display_name="Author B")
    db_session.add(a)
    db_session.commit()
    db_session.refresh(a)
    return a
