"""
Integration tests for authentication endpoints.
Each test runs inside a rolled-back DB transaction (see conftest.py).
"""
import pytest
from fastapi.testclient import TestClient

from tests.conftest import get_auth_headers


class TestRegistration:
    def test_register_success(self, client: TestClient):
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "Secure123",
                "full_name": "New User",
            },
        )
        assert response.status_code == 201
        body = response.json()
        assert body["email"] == "newuser@example.com"
        assert body["role"] == "user"
        assert "hashed_password" not in body   # Must never be exposed

    def test_register_duplicate_email(self, client: TestClient, regular_user):
        response = client.post(
            "/api/v1/auth/register",
            json={"email": regular_user.email, "password": "AnotherPass1"},
        )
        assert response.status_code == 409

    def test_register_weak_password_no_digit(self, client: TestClient):
        response = client.post(
            "/api/v1/auth/register",
            json={"email": "weak@example.com", "password": "NoDigitsHere"},
        )
        assert response.status_code == 422

    def test_register_password_too_short(self, client: TestClient):
        response = client.post(
            "/api/v1/auth/register",
            json={"email": "short@example.com", "password": "Ab1"},
        )
        assert response.status_code == 422

    def test_register_invalid_email(self, client: TestClient):
        response = client.post(
            "/api/v1/auth/register",
            json={"email": "not-an-email", "password": "Password1"},
        )
        assert response.status_code == 422


class TestLogin:
    def test_login_success(self, client: TestClient, regular_user):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": regular_user.email, "password": "Password123"},
        )
        assert response.status_code == 200
        body = response.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "bearer"
        assert body["expires_in"] > 0

    def test_login_wrong_password(self, client: TestClient, regular_user):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": regular_user.email, "password": "WrongPass999"},
        )
        assert response.status_code == 401

    def test_login_unknown_email(self, client: TestClient):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "ghost@example.com", "password": "Password1"},
        )
        assert response.status_code == 401

    def test_login_inactive_user(self, client: TestClient, regular_user, db):
        regular_user.is_active = False
        db.commit()
        response = client.post(
            "/api/v1/auth/login",
            json={"email": regular_user.email, "password": "Password123"},
        )
        assert response.status_code == 403


class TestTokenRefresh:
    def test_refresh_success(self, client: TestClient, regular_user):
        login = client.post(
            "/api/v1/auth/login",
            json={"email": regular_user.email, "password": "Password123"},
        )
        refresh_token = login.json()["refresh_token"]

        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 200
        body = response.json()
        assert "access_token" in body
        # New refresh token must be issued (token rotation)
        assert body["refresh_token"] != refresh_token

    def test_refresh_token_can_only_be_used_once(self, client: TestClient, regular_user):
        """Token rotation: replaying the original refresh token must fail."""
        login = client.post(
            "/api/v1/auth/login",
            json={"email": regular_user.email, "password": "Password123"},
        )
        refresh_token = login.json()["refresh_token"]

        # First use — succeeds
        client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})

        # Second use — must be rejected
        response = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert response.status_code == 401

    def test_refresh_with_invalid_token(self, client: TestClient):
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "this.is.not.valid"},
        )
        assert response.status_code == 401


class TestLogout:
    def test_logout_success(self, client: TestClient, regular_user):
        login = client.post(
            "/api/v1/auth/login",
            json={"email": regular_user.email, "password": "Password123"},
        )
        tokens = login.json()
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}

        response = client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": tokens["refresh_token"]},
            headers=headers,
        )
        assert response.status_code == 200
        assert "message" in response.json()

    def test_logout_invalidates_refresh_token(self, client: TestClient, regular_user):
        """After logout, the refresh token must not be usable."""
        login = client.post(
            "/api/v1/auth/login",
            json={"email": regular_user.email, "password": "Password123"},
        )
        tokens = login.json()
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}

        client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": tokens["refresh_token"]},
            headers=headers,
        )

        refresh_attempt = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )
        assert refresh_attempt.status_code == 401

    def test_logout_requires_auth(self, client: TestClient):
        response = client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": "any-token"},
        )
        assert response.status_code == 401
