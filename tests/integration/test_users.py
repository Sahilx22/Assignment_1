"""
Integration tests for user management and RBAC endpoints.
"""
import pytest
from fastapi.testclient import TestClient

from tests.conftest import get_auth_headers


class TestProtectedRoute:
    def test_get_profile_authenticated(self, client: TestClient, regular_user):
        headers = get_auth_headers(client, regular_user.email, "Password123")
        response = client.get("/api/v1/users/me", headers=headers)
        assert response.status_code == 200
        body = response.json()
        assert body["email"] == regular_user.email
        assert body["role"] == "user"

    def test_get_profile_unauthenticated(self, client: TestClient):
        response = client.get("/api/v1/users/me")
        assert response.status_code == 401

    def test_get_profile_invalid_token(self, client: TestClient):
        response = client.get(
            "/api/v1/users/me",
            headers={"Authorization": "Bearer totally.invalid.token"},
        )
        assert response.status_code == 401

    def test_update_profile(self, client: TestClient, regular_user):
        headers = get_auth_headers(client, regular_user.email, "Password123")
        response = client.patch(
            "/api/v1/users/me",
            json={"full_name": "Updated Name"},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["full_name"] == "Updated Name"


class TestRBACAdminEndpoints:
    def test_admin_can_list_users(self, client: TestClient, admin_user, regular_user):
        headers = get_auth_headers(client, admin_user.email, "AdminPass123")
        response = client.get("/api/v1/users/", headers=headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        assert len(response.json()) >= 2

    def test_regular_user_cannot_list_users(self, client: TestClient, regular_user):
        headers = get_auth_headers(client, regular_user.email, "Password123")
        response = client.get("/api/v1/users/", headers=headers)
        assert response.status_code == 403

    def test_admin_can_get_user_by_id(self, client: TestClient, admin_user, regular_user):
        headers = get_auth_headers(client, admin_user.email, "AdminPass123")
        response = client.get(f"/api/v1/users/{regular_user.id}", headers=headers)
        assert response.status_code == 200
        assert response.json()["id"] == str(regular_user.id)

    def test_regular_user_cannot_get_user_by_id(self, client: TestClient, regular_user, admin_user):
        headers = get_auth_headers(client, regular_user.email, "Password123")
        response = client.get(f"/api/v1/users/{admin_user.id}", headers=headers)
        assert response.status_code == 403

    def test_admin_can_change_user_role(self, client: TestClient, admin_user, regular_user):
        headers = get_auth_headers(client, admin_user.email, "AdminPass123")
        response = client.patch(
            f"/api/v1/users/{regular_user.id}/role",
            params={"role": "admin"},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["role"] == "admin"

    def test_admin_cannot_change_own_role(self, client: TestClient, admin_user):
        headers = get_auth_headers(client, admin_user.email, "AdminPass123")
        response = client.patch(
            f"/api/v1/users/{admin_user.id}/role",
            params={"role": "user"},
            headers=headers,
        )
        assert response.status_code == 400

    def test_admin_can_deactivate_user(self, client: TestClient, admin_user, regular_user):
        headers = get_auth_headers(client, admin_user.email, "AdminPass123")
        response = client.delete(f"/api/v1/users/{regular_user.id}", headers=headers)
        assert response.status_code == 200

    def test_deactivated_user_cannot_login(self, client: TestClient, admin_user, regular_user):
        """After deactivation, login attempts must be rejected."""
        headers = get_auth_headers(client, admin_user.email, "AdminPass123")
        client.delete(f"/api/v1/users/{regular_user.id}", headers=headers)

        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": regular_user.email, "password": "Password123"},
        )
        assert login_response.status_code == 403

    def test_admin_cannot_deactivate_self(self, client: TestClient, admin_user):
        headers = get_auth_headers(client, admin_user.email, "AdminPass123")
        response = client.delete(f"/api/v1/users/{admin_user.id}", headers=headers)
        assert response.status_code == 400


class TestHealthCheck:
    def test_health_check_is_public(self, client: TestClient):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
