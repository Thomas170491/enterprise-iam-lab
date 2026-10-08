from unittest.mock import Mock

import pytest
import requests

import services.keycloak_admin_service as admin_service

from services.exceptions import KeycloakAdminAPIError


def test_get_role_composite_children_returns_direct_children(monkeypatch):
    """
    Verify that get_role_composite_children retrieves a role's direct children.
    """
    monkeypatch.setattr(
        admin_service,
        "get_service_access_token",
        Mock(return_value="fake-service-token"),
    )

    fake_response = Mock()
    fake_response.raise_for_status.return_value = None
    fake_response.json.return_value = [
        {
            "id": "finance-viewer-id",
            "name": "finance-data-viewer",
        }
    ]

    def fake_get(url, headers, timeout):
        assert url == (
            "https://keycloak.test/admin/realms/novasecure/"
            "roles-by-id/finance-staff-id/composites"
        )
        assert headers["Authorization"] == "Bearer fake-service-token"
        assert headers["Accept"] == "application/json"
        assert timeout == 5
        return fake_response

    monkeypatch.setattr(
        admin_service.requests,
        "get",
        fake_get,
    )
    children = admin_service.get_role_composite_children(
        admin_api_url="https://keycloak.test/admin/realms/novasecure",
        token_url="https://keycloak.test/token",
        client_id="iam-governance-service",
        client_secret="fake-secret",
        role_id="finance-staff-id",
    )

    assert children == fake_response.json.return_value


def test_get_role_composite_children_rejects_http_failure(monkeypatch):
    """
    "Verify that get_role_composite_children wraps a failed Keycloak request.
    """
    monkeypatch.setattr(
        admin_service,
        "get_service_access_token",
        Mock(return_value="fake-service-token"),
    )

    fake_response = Mock()
    fake_response.raise_for_status.return_value = None
    fake_response.json.return_value = [
        {"id": "finance-viewer-id", "name": "finance-data-viewer"}
    ]

    def fake_get(url, headers, timeout):

        assert url == (
            "https://keycloak.test/admin/realms/novasecure/"
            "roles-by-id/finance-staff-id/composites"
        )
        assert headers["Authorization"] == "Bearer fake-service-token"
        assert headers["Accept"] == "application/json"
        assert timeout == 5
        return fake_response

    monkeypatch.setattr(
        admin_service.requests,
        "get",
        fake_get,
    )

    fake_response.raise_for_status.side_effect = requests.HTTPError("403 Forbidden")

    with pytest.raises(
        KeycloakAdminAPIError,
        match="Role composite children retrieval failed",
    ):
        admin_service.get_role_composite_children(
            admin_api_url="https://keycloak.test/admin/realms/novasecure",
            token_url="https://keycloak.test/token",
            client_id="iam-governance-service",
            client_secret="fake-secret",
            role_id="finance-staff-id",
        )


def test_get_role_composite_children_rejects_invalid_json(monkeypatch):
    """
    Verify that get_role_composite_children rejects malformed Keycloak JSON.
    """

    monkeypatch.setattr(
        admin_service,
        "get_service_access_token",
        Mock(return_value="fake-service-token"),
    )

    fake_response = Mock()
    fake_response.raise_for_status.return_value = None
    fake_response.json.return_value = [
        {"id": "finance-viewer-id", "name": "finance-data-viewer"}
    ]

    def fake_get(url, headers, timeout):

        assert url == (
            "https://keycloak.test/admin/realms/novasecure/"
            "roles-by-id/finance-staff-id/composites"
        )
        assert headers["Authorization"] == "Bearer fake-service-token"
        assert headers["Accept"] == "application/json"
        assert timeout == 5
        return fake_response

    monkeypatch.setattr(
        admin_service.requests,
        "get",
        fake_get,
    )

    fake_response.json.side_effect = ValueError("Bad JSON")

    with pytest.raises(
        KeycloakAdminAPIError,
        match="Unexpected JSON response",
    ):
        admin_service.get_role_composite_children(
            admin_api_url="https://keycloak.test/admin/realms/novasecure",
            token_url="https://keycloak.test/token",
            client_id="iam-governance-service",
            client_secret="fake-secret",
            role_id="finance-staff-id",
        )


def test_get_effective_realm_roles(monkeypatch):
    """Verify that effective realm-role retrieval returns the complete granted role set for a user."""
    monkeypatch.setattr(
        admin_service,
        "get_service_access_token",
        lambda **kwargs: "fake-service-token",
    )

    fake_response = Mock()

    fake_response.raise_for_status.return_value = None

    fake_response.json.return_value = [
        {"name": "employee"},
        {"name": "iam-operator"},
        {"name": "privileged-user"},
    ]

    def fake_get(
        url,
        headers,
        timeout,
    ):
        assert url == (
            "https://keycloak.test/admin/realms/"
            "novasecure/users/user-123/"
            "role-mappings/realm/composite"
        )

        assert headers["Authorization"] == ("Bearer fake-service-token")

        assert headers["Accept"] == "application/json"

        assert timeout == 5

        return fake_response

    monkeypatch.setattr(
        admin_service.requests,
        "get",
        fake_get,
    )

    roles = admin_service.get_effective_realm_roles(
        admin_api_url=("https://keycloak.test/admin/realms/novasecure"),
        token_url="https://keycloak.test/token",
        client_id="iam-governance-service",
        client_secret="fake-secret",
        user_id="user-123",
    )

    assert len(roles) == 3

    assert roles[1]["name"] == "iam-operator"
