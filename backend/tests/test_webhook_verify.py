import pytest
from fastapi import HTTPException

from app.services.webhook import verify_request_signature


def test_verify_signature_ok():
    body = b'{"book_id":"x"}'
    secret = "s"
    from app.services.webhook import sign_body

    sig = "sha256=" + sign_body(body, secret)
    verify_request_signature(sig, body, secret)


def test_verify_signature_fails():
    with pytest.raises(HTTPException) as ei:
        verify_request_signature("sha256=wrong", b"{}", "s")
    assert ei.value.status_code == 401
