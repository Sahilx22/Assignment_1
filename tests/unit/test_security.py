"""
Unit tests for app.core.security — no DB, no HTTP.
"""
import time
import pytest
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_access_token,
    verify_refresh_token,
    decode_token,
)


class TestPasswordHashing:
    def test_hash_is_not_plaintext(self):
        hashed = hash_password("MyPassword1")
        assert hashed != "MyPassword1"

    def test_correct_password_verifies(self):
        hashed = hash_password("MyPassword1")
        assert verify_password("MyPassword1", hashed) is True

    def test_wrong_password_fails(self):
        hashed = hash_password("MyPassword1")
        assert verify_password("WrongPassword", hashed) is False

    def test_different_hashes_for_same_password(self):
        """bcrypt generates a unique salt each time."""
        h1 = hash_password("MyPassword1")
        h2 = hash_password("MyPassword1")
        assert h1 != h2


class TestAccessTokens:
    def test_create_and_verify(self):
        token = create_access_token("user-123")
        subject = verify_access_token(token)
        assert subject == "user-123"

    def test_extra_claims_included(self):
        token = create_access_token("user-456", extra_claims={"role": "admin"})
        payload = decode_token(token)
        assert payload["role"] == "admin"
        assert payload["sub"] == "user-456"

    def test_token_type_is_access(self):
        token = create_access_token("user-789")
        payload = decode_token(token)
        assert payload["type"] == "access"

    def test_refresh_token_rejected_as_access(self):
        """A refresh token must not be accepted where an access token is expected."""
        refresh = create_refresh_token("user-000")
        assert verify_access_token(refresh) is None

    def test_tampered_token_rejected(self):
        token = create_access_token("user-111")
        tampered = token[:-5] + "XXXXX"
        assert verify_access_token(tampered) is None

    def test_garbage_string_rejected(self):
        assert verify_access_token("not.a.token") is None


class TestRefreshTokens:
    def test_create_and_verify(self):
        token = create_refresh_token("user-222")
        subject = verify_refresh_token(token)
        assert subject == "user-222"

    def test_token_type_is_refresh(self):
        token = create_refresh_token("user-333")
        payload = decode_token(token)
        assert payload["type"] == "refresh"

    def test_access_token_rejected_as_refresh(self):
        access = create_access_token("user-444")
        assert verify_refresh_token(access) is None
