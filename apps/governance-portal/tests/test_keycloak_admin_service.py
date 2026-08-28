from unittest.mock import Mock

from pytest import MonkeyPatch

import pytest

import services.keycloak_admin_service as admin_service

from services.exceptions import KeycloakAdminAPIError


def test_search_users(monkeypatch: MonkeyPatch):

    # We do not want this unit test contacting
    # the real Keycloak token endpoint
    monkeypatch.setattr(
        admin_service,
        "get_service_access_token",
        lambda **kwargs: "fake-service-token"
    )

    fake_response = Mock()

    fake_response.raise_for_status.return_value = None

    fake_response.json.return_value = [
        {
            "id": "user-123",
            "username": "e1004",
            "firstName": "Leo",
            "lastName": "Bernard",
            "enabled": True,
        }
    ]

    def fake_get(
        url,
        headers,
        params,
        timeout,
    ):
        assert url == (
            "https://keycloak.test/admin/realms/"
            "novasecure/users"
        )

        assert headers["Authorization"] == (
            "Bearer fake-service-token"
        )

        assert headers["Accept"] == "application/json"

        assert params == {
            "max": 20,
            "search": "e1004"
        }

        assert timeout == 5

        return fake_response

    monkeypatch.setattr(
        admin_service.requests,
        "get",
        fake_get,
    )

    users = admin_service.search_users(
        admin_api_url=(
            "https://keycloak.test/admin/realms/novasecure"
        ),
        token_url="https://keycloak.test/token",
        client_id="iam-governance-service",
        client_secret="fake-secret",
        search="e1004"
    )

    assert len(users) == 1

    assert users[0]["username"] == "e1004"


def test_get_user(monkeypatch: MonkeyPatch):

    # We do not want this unit test contacting
    # the real Keycloak token endpoint
    monkeypatch.setattr(
        admin_service,
        "get_service_access_token",
        lambda **kwargs: "fake-service-token"
    )

    fake_response = Mock()

    fake_response.raise_for_status.return_value = None

    fake_response.json.return_value = {
        "id": "user-123",
        "username": "e1004",
        "firstName": "Leo",
        "lastName": "Bernard",
        "enabled": True,
    }

    def fake_get(
        url,
        headers,
        timeout,
    ):
        assert url == (
            "https://keycloak.test/admin/realms/"
            "novasecure/users/user-123"
        )

        assert headers["Authorization"] == (
            "Bearer fake-service-token"
        )

        assert headers["Accept"] == "application/json"

        assert timeout == 5

        return fake_response

    monkeypatch.setattr(
        admin_service.requests,
        "get",
        fake_get,
    )

    user = admin_service.get_user(
        admin_api_url=(
            "https://keycloak.test/admin/realms/novasecure"
        ),
        token_url="https://keycloak.test/token",
        client_id="iam-governance-service",
        client_secret="fake-secret",
        user_id="user-123"
    )

    assert user["username"] == "e1004"


def test_get_user_groups(monkeypatch: MonkeyPatch):

    # We do not want this unit test contacting
    # the real Keycloak token endpoint
    monkeypatch.setattr(
        admin_service,
        "get_service_access_token",
        lambda **kwargs: "fake-service-token"
    )

    fake_response = Mock()

    fake_response.raise_for_status.return_value = None

    fake_response.json.return_value = [
        {
            "id": "group-123",
            "name": "IAM Operators",
        }
    ]

    def fake_get(
        url,
        headers,
        timeout,
    ):
        assert url == (
            "https://keycloak.test/admin/realms/"
            "novasecure/users/user-123/groups"
        )

        assert headers["Authorization"] == (
            "Bearer fake-service-token"
        )

        assert headers["Accept"] == "application/json"

        assert timeout == 5

        return fake_response

    monkeypatch.setattr(
        admin_service.requests,
        "get",
        fake_get,
    )

    groups = admin_service.get_user_groups(
        admin_api_url=(
            "https://keycloak.test/admin/realms/novasecure"
        ),
        token_url="https://keycloak.test/token",
        client_id="iam-governance-service",
        client_secret="fake-secret",
        user_id="user-123"
    )

    assert len(groups) == 1

    assert groups[0]["name"] == "IAM Operators"


def test_get_effective_realm_roles(
    monkeypatch: MonkeyPatch
):
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

        assert headers["Authorization"] == (
            "Bearer fake-service-token"
        )

        assert headers["Accept"] == "application/json"

        assert timeout == 5

        return fake_response

    monkeypatch.setattr(
        admin_service.requests,
        "get",
        fake_get,
    )

    roles = admin_service.get_effective_realm_roles(
        admin_api_url=(
            "https://keycloak.test/admin/realms/novasecure"
        ),
        token_url="https://keycloak.test/token",
        client_id="iam-governance-service",
        client_secret="fake-secret",
        user_id="user-123",
    )

    assert len(roles) == 3

    assert roles[1]["name"] == "iam-operator"


def test_get_client_uuid(
    monkeypatch: MonkeyPatch,
):
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
        assert url == (
            "https://keycloak.test/admin/realms/"
            "novasecure/clients"
        )

        assert params == {
            "clientId": "employee-portal"
        }

        assert headers["Authorization"] == (
            "Bearer fake-service-token"
        )

        assert headers["Accept"] == "application/json"

        assert timeout == 5

        return fake_response

    monkeypatch.setattr(
        admin_service.requests,
        "get",
        fake_get,
    )

    client_uuid = admin_service.get_client_uuid(
        admin_api_url=(
            "https://keycloak.test/admin/realms/novasecure"
        ),
        token_url="https://keycloak.test/token",
        client_id="iam-governance-service",
        client_secret="fake-secret",
        client_name="employee-portal",
    )

    assert client_uuid == "client-uuid-123"


def test_get_client_uuid_handles_missing_client(
    monkeypatch: MonkeyPatch,
):
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

    with pytest.raises(
        KeycloakAdminAPIError
    ) as exc_info:

        admin_service.get_client_uuid(
            admin_api_url=(
                "https://keycloak.test/admin/realms/novasecure"
            ),
            token_url="https://keycloak.test/token",
            client_id="iam-governance-service",
            client_secret="fake-secret",
            client_name="does-not-exist",
        )

    assert exc_info.value.reason == "Client not found"


def test_get_effective_client_roles(
    monkeypatch: MonkeyPatch
):
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
        assert admin_api_url == (
            "https://keycloak.test/admin/realms/novasecure"
        )

        assert token_url == (
            "https://keycloak.test/token"
        )

        assert client_id == (
            "iam-governance-service"
        )

        assert client_secret == "fake-secret"

        assert client_name == (
            "iam-admin-portal"
        )

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

        assert headers["Authorization"] == (
            "Bearer fake-service-token"
        )

        assert headers["Accept"] == "application/json"

        assert timeout == 5

        return fake_response

    monkeypatch.setattr(
        admin_service.requests,
        "get",
        fake_get,
    )

    roles = admin_service.get_effective_client_roles(
        admin_api_url=(
            "https://keycloak.test/admin/realms/novasecure"
        ),
        token_url="https://keycloak.test/token",
        client_id="iam-governance-service",
        client_secret="fake-secret",
        user_id="user-123",
        target_client_name="iam-admin-portal",
    )

    assert len(roles) == 3

    assert roles[0]["name"] == (
        "iam-dashboard-access"
    )

    assert roles[2]["name"] == (
        "role-manager"
    )

def test_get_client_role(monkeypatch) :
        monkeypatch.setattr(
            admin_service,
            "get_service_access_token",
            lambda  **kwargs : "fake_service_token"
        )

        fake_response = Mock()
        fake_response.raise_for_status_value.return_value = None

        fake_response.json.return_value = {
            "id" : "role-uuid-123",
            "name" : "finance-data-viewer",
            "clientRole" : True 
        }

        fake_get = Mock(
            return_value=fake_response
        )

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


        
        