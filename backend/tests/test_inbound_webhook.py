import json
from unittest.mock import patch

from app.models import Book
from app.services.webhook import sign_body


@patch("app.api.inbound_webhook_routes.run_ingest_job.delay")
def test_inbound_webhook_hmac_triggers_job(mock_delay, client, author_a, db_session):
    book = Book(author_id=author_a.id, title="Webhook book", asin="WH01")
    db_session.add(book)
    db_session.commit()
    db_session.refresh(book)

    payload = {"book_id": str(book.id), "idempotency_key": "wh-key"}
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    secret = "test-webhook-secret"
    sig = "sha256=" + sign_body(body, secret)

    r = client.post(
        "/api/v1/webhooks/ingestion",
        content=body,
        headers={"X-ReviewPulse-Signature": sig, "Content-Type": "application/json"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["deduped"] is False
    assert mock_delay.call_count == 1

    r2 = client.post(
        "/api/v1/webhooks/ingestion",
        content=body,
        headers={"X-ReviewPulse-Signature": sig, "Content-Type": "application/json"},
    )
    assert r2.status_code == 200
    assert r2.json()["deduped"] is True
    assert r2.json()["job_id"] == data["job_id"]
    assert mock_delay.call_count == 1


def test_inbound_webhook_rejects_bad_sig(client, author_a, db_session):
    book = Book(author_id=author_a.id, title="X", asin="WH02")
    db_session.add(book)
    db_session.commit()
    db_session.refresh(book)
    body = json.dumps({"book_id": str(book.id)}).encode("utf-8")
    r = client.post(
        "/api/v1/webhooks/ingestion",
        content=body,
        headers={"X-ReviewPulse-Signature": "sha256=deadbeef", "Content-Type": "application/json"},
    )
    assert r.status_code == 401
