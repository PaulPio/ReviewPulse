"""
F1 Live Integration Test
========================
Tests the full author-registration -> book-creation -> ingestion-trigger -> job-poll
flow against a running dev server at http://localhost:8000.

Run with:
    cd backend && .venv\\Scripts\\python -m pytest tests/test_f1_live.py -v

Requirements:
    - Server must be running: uvicorn app.main:app --port 8000
    - httpx must be installed in the venv
"""

from __future__ import annotations

import uuid

import httpx
import pytest

BASE_URL = "http://localhost:8000/api/v1"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Module-scoped fixtures — one server round-trip per test session
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def registered_author() -> dict:
    """
    Register a fresh author and return the full TokenOut payload.
    Uses a uuid-based email so re-runs never conflict.
    """
    unique_id = uuid.uuid4().hex[:12]
    payload = {
        "email": f"f1test_{unique_id}@example.com",
        "password": f"Test{unique_id[:8]}1",   # letters + digit, >= 8 chars
        "display_name": f"F1 Tester {unique_id}",
    }
    resp = httpx.post(f"{BASE_URL}/auth/register", json=payload)
    assert resp.status_code == 201, (
        f"Registration failed: {resp.status_code} — {resp.text}"
    )
    data = resp.json()
    assert "access_token" in data, f"No access_token in response: {data}"
    assert data["token_type"] == "bearer"
    assert "author" in data
    assert "id" in data["author"]
    return data


@pytest.fixture(scope="module")
def token(registered_author: dict) -> str:
    return registered_author["access_token"]


@pytest.fixture(scope="module")
def author_id(registered_author: dict) -> str:
    return registered_author["author"]["id"]


# ---------------------------------------------------------------------------
# 1. Registration assertions
# ---------------------------------------------------------------------------

class TestRegisterAuthor:
    def test_register_returns_201(self, registered_author: dict):
        """Status code 201 and token_type=bearer are present."""
        # The fixture already asserts 201; this test documents the assertion.
        assert registered_author["token_type"] == "bearer"

    def test_register_returns_access_token(self, registered_author: dict):
        assert isinstance(registered_author["access_token"], str)
        assert len(registered_author["access_token"]) > 20

    def test_register_returns_author_id(self, registered_author: dict):
        author = registered_author["author"]
        assert "id" in author
        # Must be a valid UUID string
        uuid.UUID(author["id"])

    def test_register_conflict_returns_409(self, registered_author: dict):
        """Registering the same email a second time must return 409."""
        email = registered_author["author"]["email"]
        resp = httpx.post(
            f"{BASE_URL}/auth/register",
            json={
                "email": email,
                "password": "AnotherPass99",
                "display_name": "Duplicate",
            },
        )
        assert resp.status_code == 409, (
            f"Expected 409 on duplicate email, got {resp.status_code}: {resp.text}"
        )


# ---------------------------------------------------------------------------
# 2. Book creation
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def book_a(token: str) -> dict:
    """Book A: title only."""
    resp = httpx.post(
        f"{BASE_URL}/books",
        json={"title": "The Last Algorithm"},
        headers=_auth_headers(token),
    )
    assert resp.status_code == 201, f"Book A creation failed: {resp.status_code} — {resp.text}"
    return resp.json()


@pytest.fixture(scope="module")
def book_b(token: str) -> dict:
    """Book B: title + ISBN."""
    resp = httpx.post(
        f"{BASE_URL}/books",
        json={"title": "Rust & Redemption", "isbn": "9781234567890"},
        headers=_auth_headers(token),
    )
    assert resp.status_code == 201, f"Book B creation failed: {resp.status_code} — {resp.text}"
    return resp.json()


@pytest.fixture(scope="module")
def book_c(token: str) -> dict:
    """Book C: title + amazon_url."""
    resp = httpx.post(
        f"{BASE_URL}/books",
        json={
            "title": "Echoes in the Dark",
            "amazon_url": "https://amazon.com/dp/B0EXAMPLE",
        },
        headers=_auth_headers(token),
    )
    assert resp.status_code == 201, f"Book C creation failed: {resp.status_code} — {resp.text}"
    return resp.json()


class TestAddBooks:
    def test_book_a_title_only(self, book_a: dict):
        assert book_a["title"] == "The Last Algorithm"
        assert book_a["isbn"] is None
        assert book_a["amazon_url"] is None
        uuid.UUID(book_a["id"])  # valid UUID

    def test_book_b_title_and_isbn(self, book_b: dict):
        assert book_b["title"] == "Rust & Redemption"
        assert book_b["isbn"] == "9781234567890"
        uuid.UUID(book_b["id"])

    def test_book_c_title_and_amazon_url(self, book_c: dict):
        assert book_c["title"] == "Echoes in the Dark"
        assert book_c["amazon_url"] == "https://amazon.com/dp/B0EXAMPLE"
        uuid.UUID(book_c["id"])

    def test_books_belong_to_registered_author(
        self, book_a: dict, book_b: dict, book_c: dict, author_id: str
    ):
        for book, label in [(book_a, "A"), (book_b, "B"), (book_c, "C")]:
            assert book["author_id"] == author_id, (
                f"Book {label} author_id mismatch: {book['author_id']} != {author_id}"
            )

    def test_book_unauthenticated_returns_401(self):
        resp = httpx.post(
            f"{BASE_URL}/books",
            json={"title": "No Auth Book"},
        )
        assert resp.status_code == 401, (
            f"Expected 401 without auth, got {resp.status_code}"
        )


# ---------------------------------------------------------------------------
# 3. Trigger ingestion jobs
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def job_a(token: str, book_a: dict) -> dict:
    resp = httpx.post(
        f"{BASE_URL}/jobs/books/{book_a['id']}/ingest",
        headers=_auth_headers(token),
    )
    assert resp.status_code == 202, (
        f"Job A trigger failed: {resp.status_code} — {resp.text}"
    )
    return resp.json()


@pytest.fixture(scope="module")
def job_b(token: str, book_b: dict) -> dict:
    resp = httpx.post(
        f"{BASE_URL}/jobs/books/{book_b['id']}/ingest",
        headers=_auth_headers(token),
    )
    assert resp.status_code == 202, (
        f"Job B trigger failed: {resp.status_code} — {resp.text}"
    )
    return resp.json()


@pytest.fixture(scope="module")
def job_c(token: str, book_c: dict) -> dict:
    resp = httpx.post(
        f"{BASE_URL}/jobs/books/{book_c['id']}/ingest",
        headers=_auth_headers(token),
    )
    assert resp.status_code == 202, (
        f"Job C trigger failed: {resp.status_code} — {resp.text}"
    )
    return resp.json()


ACCEPTED_STATUSES = {"queued", "running", "completed", "partial"}


class TestTriggerIngestion:
    def test_job_a_returns_202_and_queued(self, job_a: dict, book_a: dict):
        assert job_a["book_id"] == book_a["id"]
        assert job_a["status"] in ACCEPTED_STATUSES, (
            f"Job A status unexpected: {job_a['status']}"
        )
        uuid.UUID(job_a["id"])

    def test_job_b_returns_202_and_queued(self, job_b: dict, book_b: dict):
        assert job_b["book_id"] == book_b["id"]
        assert job_b["status"] in ACCEPTED_STATUSES, (
            f"Job B status unexpected: {job_b['status']}"
        )
        uuid.UUID(job_b["id"])

    def test_job_c_returns_202_and_queued(self, job_c: dict, book_c: dict):
        assert job_c["book_id"] == book_c["id"]
        assert job_c["status"] in ACCEPTED_STATUSES, (
            f"Job C status unexpected: {job_c['status']}"
        )
        uuid.UUID(job_c["id"])

    def test_job_status_not_failed(self, job_a: dict, job_b: dict, job_c: dict):
        for job, label in [(job_a, "A"), (job_b, "B"), (job_c, "C")]:
            assert job["status"] != "failed", (
                f"Job {label} was immediately 'failed': {job}"
            )

    def test_ingest_conflict_returns_409(self, token: str, book_a: dict):
        """
        A second ingest request on the same book (while the first job is
        still queued/running) must return 409.
        """
        resp = httpx.post(
            f"{BASE_URL}/jobs/books/{book_a['id']}/ingest",
            headers=_auth_headers(token),
        )
        assert resp.status_code == 409, (
            f"Expected 409 on duplicate ingest, got {resp.status_code}: {resp.text}"
        )

    def test_ingest_unknown_book_returns_404(self, token: str):
        fake_id = uuid.uuid4()
        resp = httpx.post(
            f"{BASE_URL}/jobs/books/{fake_id}/ingest",
            headers=_auth_headers(token),
        )
        assert resp.status_code == 404, (
            f"Expected 404 for unknown book, got {resp.status_code}: {resp.text}"
        )

    def test_ingest_unauthenticated_returns_401(self, book_a: dict):
        resp = httpx.post(f"{BASE_URL}/jobs/books/{book_a['id']}/ingest")
        assert resp.status_code == 401, (
            f"Expected 401 without auth on ingest, got {resp.status_code}"
        )


# ---------------------------------------------------------------------------
# 4. Poll job status
# ---------------------------------------------------------------------------

class TestPollJobStatus:
    def test_poll_job_a(self, token: str, job_a: dict):
        resp = httpx.get(
            f"{BASE_URL}/jobs/{job_a['id']}",
            headers=_auth_headers(token),
        )
        assert resp.status_code == 200, (
            f"Poll job A failed: {resp.status_code} — {resp.text}"
        )
        data = resp.json()
        assert data["id"] == job_a["id"]
        assert data["status"] in ACCEPTED_STATUSES, (
            f"Job A polled status unexpected: {data['status']}"
        )
        assert data["status"] != "failed", f"Job A is failed: {data}"

    def test_poll_job_b(self, token: str, job_b: dict):
        resp = httpx.get(
            f"{BASE_URL}/jobs/{job_b['id']}",
            headers=_auth_headers(token),
        )
        assert resp.status_code == 200, (
            f"Poll job B failed: {resp.status_code} — {resp.text}"
        )
        data = resp.json()
        assert data["id"] == job_b["id"]
        assert data["status"] in ACCEPTED_STATUSES
        assert data["status"] != "failed", f"Job B is failed: {data}"

    def test_poll_job_c(self, token: str, job_c: dict):
        resp = httpx.get(
            f"{BASE_URL}/jobs/{job_c['id']}",
            headers=_auth_headers(token),
        )
        assert resp.status_code == 200, (
            f"Poll job C failed: {resp.status_code} — {resp.text}"
        )
        data = resp.json()
        assert data["id"] == job_c["id"]
        assert data["status"] in ACCEPTED_STATUSES
        assert data["status"] != "failed", f"Job C is failed: {data}"

    def test_poll_job_returns_correct_fields(self, token: str, job_a: dict):
        """Verify all expected JobOut fields are present in the poll response."""
        resp = httpx.get(
            f"{BASE_URL}/jobs/{job_a['id']}",
            headers=_auth_headers(token),
        )
        assert resp.status_code == 200
        data = resp.json()
        required_fields = {
            "id", "book_id", "author_id", "status",
            "total_reviews", "processed_reviews", "failed_reviews",
            "created_at",
        }
        missing = required_fields - data.keys()
        assert not missing, f"Missing fields in job poll response: {missing}"

    def test_poll_unknown_job_returns_404(self, token: str):
        fake_id = uuid.uuid4()
        resp = httpx.get(
            f"{BASE_URL}/jobs/{fake_id}",
            headers=_auth_headers(token),
        )
        assert resp.status_code == 404, (
            f"Expected 404 for unknown job, got {resp.status_code}: {resp.text}"
        )

    def test_poll_unauthenticated_returns_401(self, job_a: dict):
        resp = httpx.get(f"{BASE_URL}/jobs/{job_a['id']}")
        assert resp.status_code == 401, (
            f"Expected 401 without auth on poll, got {resp.status_code}"
        )
