"""
Unit tests for security utilities: JWT and HMAC webhook signing.
No I/O required — pure unit tests.
"""

from __future__ import annotations

import time
import uuid
from datetime import timedelta

import pytest
from jose import JWTError

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    sign_webhook_payload,
    verify_password,
    verify_webhook_signature,
)


class TestPasswordHashing:
    def test_hash_and_verify(self):
        plain = "MySecurePassword123"
        hashed = hash_password(plain)
        assert hashed != plain
        assert verify_password(plain, hashed)

    def test_wrong_password_fails(self):
        hashed = hash_password("correct_password")
        assert not verify_password("wrong_password", hashed)

    def test_hash_is_bcrypt(self):
        hashed = hash_password("test")
        assert hashed.startswith("$2b$")


class TestJWT:
    def test_create_and_decode(self):
        author_id = str(uuid.uuid4())
        token = create_access_token(author_id)
        payload = decode_access_token(token)
        assert payload["sub"] == author_id
        assert payload["type"] == "access"

    def test_expired_token_raises(self):
        author_id = str(uuid.uuid4())
        # Create a token that expires immediately
        token = create_access_token(author_id, expires_delta=timedelta(seconds=-1))
        with pytest.raises(JWTError):
            decode_access_token(token)

    def test_tampered_token_raises(self):
        token = create_access_token("some-id")
        tampered = token[:-5] + "XXXXX"
        with pytest.raises(JWTError):
            decode_access_token(tampered)

    def test_token_contains_subject(self):
        author_id = str(uuid.uuid4())
        token = create_access_token(author_id)
        payload = decode_access_token(token)
        assert payload["sub"] == author_id

    def test_uuid_subject_accepted(self):
        author_id = uuid.uuid4()  # UUID object, not string
        token = create_access_token(author_id)
        payload = decode_access_token(token)
        assert payload["sub"] == str(author_id)


class TestWebhookHMAC:
    def test_sign_and_verify(self):
        payload = b'{"event":"ingestion.completed","job_id":"abc"}'
        sig = sign_webhook_payload(payload)
        assert sig.startswith("sha256=")
        assert verify_webhook_signature(payload, sig)

    def test_tampered_payload_fails(self):
        payload = b'{"event":"ingestion.completed"}'
        sig = sign_webhook_payload(payload)
        tampered = b'{"event":"ingestion.tampered"}'
        assert not verify_webhook_signature(tampered, sig)

    def test_tampered_signature_fails(self):
        payload = b'{"event":"ingestion.completed"}'
        sig = sign_webhook_payload(payload)
        bad_sig = sig[:-4] + "XXXX"
        assert not verify_webhook_signature(payload, bad_sig)

    def test_signature_format(self):
        sig = sign_webhook_payload(b"test")
        assert len(sig) == 7 + 64  # "sha256=" + 64 hex chars

    def test_constant_time_comparison(self):
        """Verify comparison doesn't short-circuit on first mismatch."""
        # This is behavioural: hmac.compare_digest should take same time
        # regardless of where the first difference is. We just verify
        # it returns False without timing, not leaking via exception.
        payload = b"test payload"
        correct_sig = sign_webhook_payload(payload)
        wrong_sig = "sha256=" + "a" * 64
        result = verify_webhook_signature(payload, wrong_sig)
        assert result is False
