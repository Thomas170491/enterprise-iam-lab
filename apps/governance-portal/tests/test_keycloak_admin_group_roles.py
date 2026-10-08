from unittest.mock import Mock

import pytest
import requests

import services.keycloak_admin_service as admin_service

from services.exceptions import KeycloakAdminAPIError


def test_get_group_role_mappings_returns_mappings(monkeypatch):
    """
    Verify that group role mappings are retrieved and returned unchanged.
    """
    monkeypatch.setattr(
        admin_service, "get_service_access_token", lambda **kwargs: "fake-service-token"
    )

    payload = {
        "realmMappings": [{"id": "realm-role-123", "name": "employee"}],
        "clientMappings": {
            "employee-portal": {
                "id": "client-123",
                "client": "employee-portal",
                "mappings": [{"id": "role-123", "name": "finance-data-viewer"}],
            }
        },
    }
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = payload

    def fake_get(url, headers, timeout):
        assert url.endswith("/groups/group-123/role-mappings")
        assert headers["Authorization"] == "Bearer fake-service-token"
        assert headers["Accept"] == "application/json"
        assert timeout == 5
        return response

    monkeypatch.setattr(admin_service.requests, "get", fake_get)

    mappings = admin_service.get_group_role_mappings(
        admin_api_url="https://keycloak.test/admin/realms/novasecure",
        token_url="https://keycloak.test/token",
        client_id="iam-governance-service",
        client_secret="fake-secret",
        group_id="group-123",
    )

    assert mappings == payload
    response.json.assert_called_once()


def test_get_group_role_mappings_rejects_invalid_json(monkeypatch):
    """
    Verify that invalid JSON raises a Keycloak Admin API error.
    """
    monkeypatch.setattr(
        admin_service, "get_service_access_token", lambda **kwargs: "fake-service-token"
    )

    response = Mock()
    response.raise_for_status.return_value = None
    response.json.side_effect = ValueError("invalid JSON")
    monkeypatch.setattr(admin_service.requests, "get", lambda *args, **kwargs: response)

    with pytest.raises(
        KeycloakAdminAPIError,
        match="Invalid JSON response",
    ):
        admin_service.get_group_role_mappings(
            admin_api_url="https://keycloak.test/admin/realms/novasecure",
            token_url="https://keycloak.test/token",
            client_id="iam-governance-service",
            client_secret="fake-secret",
            group_id="group-123",
        )


def test_get_group_role_mappings_propagates_request_failure(monkeypatch):
    """
    Verify that a failed group role lookup raises a Keycloak Admin API error.
    """
    monkeypatch.setattr(
        admin_service,
        "get_service_access_token",
        lambda **kwargs: "fake-service-token",
    )

    response = Mock()
    response.raise_for_status.side_effect = requests.HTTPError("403 Forbidden")
    monkeypatch.setattr(admin_service.requests, "get", lambda *args, **kwargs: response)

    with pytest.raises(
        KeycloakAdminAPIError,
        match="Group role mapping retrieval failed",
    ):
        admin_service.get_group_role_mappings(
            admin_api_url="https://keycloak.test/admin/realms/novasecure",
            token_url="https://keycloak.test/token",
            client_id="iam-governance-service",
            client_secret="fake-secret",
            group_id="group-123",
        )

    response.json.assert_not_called()


@pytest.mark.parametrize("payload", [[], "invalid", None])
def test_get_group_role_mappings_rejects_invalid_structure(monkeypatch, payload):
    """
    Verify that group role mappings must be a dictionary.
    """
    monkeypatch.setattr(
        admin_service,
        "get_service_access_token",
        lambda **kwargs: "fake-service-token",
    )

    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = payload
    monkeypatch.setattr(admin_service.requests, "get", lambda *args, **kwargs: response)

    with pytest.raises(
        KeycloakAdminAPIError,
        match="Unexpected group role mappings response",
    ):
        admin_service.get_group_role_mappings(
            admin_api_url="https://keycloak.test/admin/realms/novasecure",
            token_url="https://keycloak.test/token",
            client_id="iam-governance-service",
            client_secret="fake-secret",
            group_id="group-123",
        )


def test_get_group_effective_client_roles(monkeypatch):
    """
    Verify that effective group client roles are retrieved from Keycloak's composite endpoint.
    """

    def fake_get_client_uuid(**kwargs):
        assert kwargs["client_name"] == "employee-portal"
        return "client-uuid-123"

    monkeypatch.setattr(
        admin_service,
        "get_client_uuid",
        fake_get_client_uuid,
    )

    monkeypatch.setattr(
        admin_service, "get_service_access_token", lambda **kwargs: "fake-service-token"
    )

    fake_response = Mock()

    fake_response.raise_for_status.return_value = None

    fake_response.json.return_value = [
        {"name": "finance-data-viewer", "id": "role-id-1"},
    ]

    def fake_get(
        url,
        headers,
        timeout,
    ):
        assert url == (
            "https://keycloak.test/admin/realms/"
            "novasecure/groups/group-123/role-mappings/clients/client-uuid-123/composite"
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

    role = admin_service.get_group_effective_client_roles(
        admin_api_url=("https://keycloak.test/admin/realms/novasecure"),
        token_url="https://keycloak.test/token",
        client_id="iam-governance-service",
        client_secret="fake-secret",
        group_id="group-123",
        target_client_name="employee-portal",
    )

    assert role == fake_response.json.return_value


def test_get_group_effective_client_roles_rejects_http_failure(monkeypatch):
    """
    Verify that a failed Keycloak request raises KeycloakAdminAPIError.
    """

    def fake_get_client_uuid(**kwargs):
        assert kwargs["client_name"] == "employee-portal"
        return "client-uuid-123"

    monkeypatch.setattr(
        admin_service,
        "get_client_uuid",
        fake_get_client_uuid,
    )

    monkeypatch.setattr(
        admin_service, "get_service_access_token", lambda **kwargs: "fake-service-token"
    )

    fake_response = Mock()

    fake_response.raise_for_status.side_effect = admin_service.requests.HTTPError(
        "403 Forbidden"
    )

    def fake_get(
        url,
        headers,
        timeout,
    ):
        assert url == (
            "https://keycloak.test/admin/realms/"
            "novasecure/groups/group-123/role-mappings/clients/client-uuid-123/composite"
        )

        assert headers["Authorization"] == ("Bearer fake-service-token")

        assert headers["Accept"] == "application/json"

        assert timeout == 5

        return fake_response

    monkeypatch.setattr(admin_service.requests, "get", fake_get)

    with pytest.raises(
        KeycloakAdminAPIError, match="Group effective client roles retrieval failed"
    ):
        admin_service.get_group_effective_client_roles(
            admin_api_url=("https://keycloak.test/admin/realms/novasecure"),
            token_url="https://keycloak.test/token",
            client_id="iam-governance-service",
            client_secret="fake-secret",
            group_id="group-123",
            target_client_name="employee-portal",
        )

    fake_response.json().assert_not_called()


def test_get_group_effective_client_roles_rejects_invalid_json(monkeypatch):
    """
    Verify that an invalid Keycloak JSON response raises KeycloakAdminAPIError.
    """

    def fake_get_client_uuid(**kwargs):
        assert kwargs["client_name"] == "employee-portal"
        return "client-uuid-123"

    monkeypatch.setattr(
        admin_service,
        "get_client_uuid",
        fake_get_client_uuid,
    )

    monkeypatch.setattr(
        admin_service, "get_service_access_token", lambda **kwargs: "fake-service-token"
    )

    fake_response = Mock()
    fake_response.json.side_effect = ValueError("bad JSON")

    def fake_get(
        url,
        headers,
        timeout,
    ):
        assert url == (
            "https://keycloak.test/admin/realms/"
            "novasecure/groups/group-123/role-mappings/clients/client-uuid-123/composite"
        )

        assert headers["Authorization"] == ("Bearer fake-service-token")

        assert headers["Accept"] == "application/json"

        assert timeout == 5

        return fake_response

    monkeypatch.setattr(admin_service.requests, "get", fake_get)

    with pytest.raises(KeycloakAdminAPIError, match="Invalid JSON response"):
        admin_service.get_group_effective_client_roles(
            admin_api_url=("https://keycloak.test/admin/realms/novasecure"),
            token_url="https://keycloak.test/token",
            client_id="iam-governance-service",
            client_secret="fake-secret",
            group_id="group-123",
            target_client_name="employee-portal",
        )


@pytest.mark.parametrize("payload", [{"id": "role-id-1"}, ["not-a-role-object"]])
def test_get_group_effective_client_roles_rejects_invalid_structure(
    monkeypatch, payload
):
    """
    Verify that effective group roles must be a list of role objects.
    """

    def fake_get_client_uuid(**kwargs):
        assert kwargs["client_name"] == "employee-portal"
        return "client-uuid-123"

    monkeypatch.setattr(
        admin_service,
        "get_client_uuid",
        fake_get_client_uuid,
    )

    monkeypatch.setattr(
        admin_service, "get_service_access_token", lambda **kwargs: "fake-service-token"
    )

    fake_response = Mock()
    fake_response.json.return_value = payload

    def fake_get(
        url,
        headers,
        timeout,
    ):
        assert url == (
            "https://keycloak.test/admin/realms/"
            "novasecure/groups/group-123/role-mappings/clients/client-uuid-123/composite"
        )

        assert headers["Authorization"] == ("Bearer fake-service-token")

        assert headers["Accept"] == "application/json"

        assert timeout == 5

        return fake_response

    monkeypatch.setattr(admin_service.requests, "get", fake_get)

    with pytest.raises(
        KeycloakAdminAPIError, match="Unexpected group effective client role response"
    ):
        admin_service.get_group_effective_client_roles(
            admin_api_url=("https://keycloak.test/admin/realms/novasecure"),
            token_url="https://keycloak.test/token",
            client_id="iam-governance-service",
            client_secret="fake-secret",
            group_id="group-123",
            target_client_name="employee-portal",
        )
