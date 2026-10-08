from unittest.mock import Mock

from pytest import MonkeyPatch

import pytest

import services.keycloak_admin_service as admin_service

from services.exceptions import KeycloakAdminAPIError


def test_get_client_uuid(monkeypatch):
    """
    Verify that a client name resolves to its Keycloak client UUID.
    """
    monkeypatch.setattr(
        admin_service,
        "get_service_access_token",
        lambda **kwargs: "fake-service-token",
    )

    fake_response = Mock()

    fake_response.raise_for_status.return_value = None

    fake_response.json.return_value = [
        {
            "id": "client-uuid-123",
            "clientId": "employee-portal",
        }
    ]

    def fake_get(
        url,
        headers,
        params,
        timeout,
    ):
        assert url == ("https://keycloak.test/admin/realms/" "novasecure/clients")

        assert params == {"clientId": "employee-portal"}

        assert headers["Authorization"] == ("Bearer fake-service-token")

        assert headers["Accept"] == "application/json"

        assert timeout == 5

        return fake_response

    monkeypatch.setattr(
        admin_service.requests,
        "get",
        fake_get,
    )

    client_uuid = admin_service.get_client_uuid(
        admin_api_url=("https://keycloak.test/admin/realms/novasecure"),
        token_url="https://keycloak.test/token",
        client_id="iam-governance-service",
        client_secret="fake-secret",
        client_name="employee-portal",
    )

    assert client_uuid == "client-uuid-123"


def test_get_client_uuid_handles_missing_client(
    monkeypatch: MonkeyPatch,
):
    """
    Verify that a missing client returns the expected empty result instead of crashing.
    """
    monkeypatch.setattr(
        admin_service,
        "get_service_access_token",
        lambda **kwargs: "fake-service-token",
    )

    fake_response = Mock()

    fake_response.raise_for_status.return_value = None

    fake_response.json.return_value = []

    monkeypatch.setattr(
        admin_service.requests,
        "get",
        lambda *args, **kwargs: fake_response,
    )

    with pytest.raises(KeycloakAdminAPIError) as exc_info:

        admin_service.get_client_uuid(
            admin_api_url=("https://keycloak.test/admin/realms/novasecure"),
            token_url="https://keycloak.test/token",
            client_id="iam-governance-service",
            client_secret="fake-secret",
            client_name="does-not-exist",
        )

    assert exc_info.value.reason == "Client not found"


def test_get_effective_client_roles(monkeypatch: MonkeyPatch):
    """
    Verify that effective client-role lookup returns the user's granted client roles.
    """
    monkeypatch.setattr(
        admin_service,
        "get_service_access_token",
        lambda **kwargs: "fake-service-token",
    )

    def fake_get_client_uuid(
        admin_api_url,
        token_url,
        client_id,
        client_secret,
        client_name,
    ):
        assert admin_api_url == ("https://keycloak.test/admin/realms/novasecure")

        assert token_url == ("https://keycloak.test/token")

        assert client_id == ("iam-governance-service")

        assert client_secret == "fake-secret"

        assert client_name == ("iam-admin-portal")

        return "client-uuid-123"

    monkeypatch.setattr(
        admin_service,
        "get_client_uuid",
        fake_get_client_uuid,
    )

    fake_response = Mock()

    fake_response.raise_for_status.return_value = None

    fake_response.json.return_value = [
        {
            "id": "role-1",
            "name": "iam-dashboard-access",
        },
        {
            "id": "role-2",
            "name": "identity-viewer",
        },
        {
            "id": "role-3",
            "name": "role-manager",
        },
    ]

    def fake_get(
        url,
        headers,
        timeout,
    ):
        assert url == (
            "https://keycloak.test/admin/realms/"
            "novasecure/users/user-123/"
            "role-mappings/clients/"
            "client-uuid-123/composite"
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

    roles = admin_service.get_effective_client_roles(
        admin_api_url=("https://keycloak.test/admin/realms/novasecure"),
        token_url="https://keycloak.test/token",
        client_id="iam-governance-service",
        client_secret="fake-secret",
        user_id="user-123",
        target_client_name="iam-admin-portal",
    )

    assert len(roles) == 3

    assert roles[0]["name"] == ("iam-dashboard-access")

    assert roles[2]["name"] == ("role-manager")


def test_get_client_role(monkeypatch):
    """
    Verify that a direct client role lookup returns the matching role metadata.
    """
    monkeypatch.setattr(
        admin_service, "get_service_access_token", lambda **kwargs: "fake_service_token"
    )

    fake_response = Mock()
    fake_response.raise_for_status_value.return_value = None

    fake_response.json.return_value = {
        "id": "role-uuid-123",
        "name": "finance-data-viewer",
        "clientRole": True,
    }

    fake_get = Mock(return_value=fake_response)

    monkeypatch.setattr(
        admin_service.requests,
        "get",
        fake_get,
    )

    role = admin_service.get_client_role(
        admin_api_url="https://keycloak.test/admin/realms/novasecure",
        token_url="https://keycloak.test/token",
        client_id="iam-governance-service",
        client_secret="fake-secret",
        client_uuid="client-uuid-123",
        role_name="finance-data-viewer",
    )

    fake_get.assert_called_once_with(
        (
            "https://keycloak.test/admin/realms/"
            "novasecure/clients/client-uuid-123/"
            "roles/finance-data-viewer"
        ),
        headers={
            "Authorization": "Bearer fake_service_token",
            "Accept": "application/json",
        },
        timeout=5,
    )

    assert role["id"] == "role-uuid-123"
    assert role["name"] == "finance-data-viewer"


def test_assign_client_role(monkeypatch):
    """
    Verify that assigning a client role posts the expected Keycloak request and returns success.
    """
    monkeypatch.setattr(
        admin_service,
        "get_service_access_token",
        lambda **kwargs: "fake_service_token",
    )

    fake_response = Mock()
    fake_response.raise_for_status.return_value = None

    fake_post = Mock(return_value=fake_response)

    monkeypatch.setattr(
        admin_service.requests,
        "post",
        fake_post,
    )

    role = {
        "id": "role-uuid-123",
        "name": "finance-data-viewer",
        "clientRole": True,
    }

    admin_service.assign_client_role(
        admin_api_url=("https://keycloak.test/admin/realms/novasecure"),
        token_url="https://keycloak.test/token",
        client_id="iam-governance-service",
        client_secret="fake-secret",
        user_id="user-123",
        client_uuid="client-uuid-123",
        role=role,
    )

    fake_post.assert_called_once_with(
        (
            "https://keycloak.test/admin/realms/"
            "novasecure/users/user-123/"
            "role-mappings/clients/client-uuid-123"
        ),
        headers={
            "Authorization": "Bearer fake_service_token",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        json=[role],
        timeout=5,
    )

    fake_response.raise_for_status.assert_called_once_with()


def test_assign_client_role_handles_http_error(monkeypatch):
    """
    Verify that client-role assignment surfaces HTTP failures as Keycloak API errors.
    """
    monkeypatch.setattr(
        admin_service,
        "get_service_access_token",
        lambda **kwargs: "fake_service_token",
    )

    fake_response = Mock()

    fake_response.raise_for_status.side_effect = admin_service.requests.HTTPError(
        "403 Forbidden"
    )

    monkeypatch.setattr(
        admin_service.requests,
        "post",
        Mock(return_value=fake_response),
    )

    role = {
        "id": "role-uuid-123",
        "name": "finance-data-viewer",
        "clientRole": True,
    }

    with pytest.raises(
        KeycloakAdminAPIError,
        match="Client role assignment failed",
    ):
        admin_service.assign_client_role(
            admin_api_url=("https://keycloak.test/admin/realms/novasecure"),
            token_url="https://keycloak.test/token",
            client_id="iam-governance-service",
            client_secret="fake-secret",
            user_id="user-123",
            client_uuid="client-uuid-123",
            role=role,
        )


def test_remove_client_role(monkeypatch):
    """
    Verify that removing a client role deletes the expected Keycloak role assignment.
    """

    monkeypatch.setattr(
        admin_service,
        "get_service_access_token",
        lambda **kwargs: "fake_service_token",
    )

    fake_response = Mock()
    fake_response.raise_for_status.return_value = None

    fake_delete = Mock(return_value=fake_response)

    monkeypatch.setattr(
        admin_service.requests,
        "delete",
        fake_delete,
    )

    role = {
        "id": "role-uuid-123",
        "name": "finance-data-viewer",
        "clientRole": True,
    }

    admin_service.remove_client_role(
        admin_api_url=("https://keycloak.test/admin/realms/novasecure"),
        token_url="https://keycloak.test/token",
        client_id="iam-governance-service",
        client_secret="fake-secret",
        user_id="user-123",
        client_uuid="client-uuid-123",
        role=role,
    )

    fake_delete.assert_called_once_with(
        (
            "https://keycloak.test/admin/realms/"
            "novasecure/users/user-123/"
            "role-mappings/clients/client-uuid-123"
        ),
        headers={
            "Authorization": "Bearer fake_service_token",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        json=[role],
        timeout=5,
    )

    fake_response.raise_for_status.assert_called_once_with()


def test_remove_client_role_handles_http_error(monkeypatch):
    """Verify that client-role removal surfaces HTTP failures as Keycloak API errors."""
    monkeypatch.setattr(
        admin_service,
        "get_service_access_token",
        lambda **kwargs: "fake_service_token",
    )

    fake_response = Mock()

    fake_response.raise_for_status.side_effect = admin_service.requests.HTTPError(
        "403 Forbidden"
    )

    monkeypatch.setattr(
        admin_service.requests,
        "delete",
        Mock(return_value=fake_response),
    )

    role = {
        "id": "role-uuid-123",
        "name": "finance-data-viewer",
        "clientRole": True,
    }

    with pytest.raises(
        KeycloakAdminAPIError,
        match="Client role removal failed",
    ):
        admin_service.remove_client_role(
            admin_api_url=("https://keycloak.test/admin/realms/novasecure"),
            token_url="https://keycloak.test/token",
            client_id="iam-governance-service",
            client_secret="fake-secret",
            user_id="user-123",
            client_uuid="client-uuid-123",
            role=role,
        )


def test_get_direct_client_roles(monkeypatch):
    """Verify that direct client-role lookup returns the roles assigned to the user for a target client."""

    monkeypatch.setattr(
        admin_service, "get_service_access_token", lambda **kwargs: "fake-service-token"
    )

    monkeypatch.setattr(
        admin_service, "get_client_uuid", lambda **kwargs: "client-uuid-123"
    )

    fake_response = Mock()

    fake_response.raise_for_status.return_value = None

    fake_response.json.return_value = [
        {
            "id": "role-1",
            "name": "finance-data-viewer",
        },
        {
            "id": "role-2",
            "name": "manager-dashboard",
        },
    ]

    fake_get = Mock(return_value=fake_response)
    monkeypatch.setattr(admin_service.requests, "get", fake_get)

    roles = admin_service.get_direct_client_roles(
        admin_api_url=("https://keycloak.test/admin/realms/novasecure"),
        token_url="https://keycloak.test/token",
        client_id="iam-governance-service",
        client_secret="fake-secret",
        user_id="user-123",
        target_client_name="employee-portal",
    )

    assert len(roles) == 2

    assert roles[0]["name"] == ("finance-data-viewer")

    assert roles[1]["name"] == ("manager-dashboard")

    fake_get.assert_called_once_with(
        (
            "https://keycloak.test/admin/realms/"
            "novasecure/users/user-123/"
            "role-mappings/clients/client-uuid-123"
        ),
        headers={
            "Authorization": "Bearer fake-service-token",
            "Accept": "application/json",
        },
        timeout=5,
    )
