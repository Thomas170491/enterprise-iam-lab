from unittest.mock import Mock

from pytest import MonkeyPatch

import pytest
import requests

import services.keycloak_admin_service as admin_service

from services.exceptions import KeycloakAdminAPIError


def test_search_users(monkeypatch: MonkeyPatch):
    """
    Verify that a user-search query returns the expected Keycloak user matches.
    """

    # We do not want this unit test contacting
    # the real Keycloak token endpoint
    monkeypatch.setattr(
        admin_service, "get_service_access_token", lambda **kwargs: "fake-service-token"
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
        assert url == ("https://keycloak.test/admin/realms/" "novasecure/users")

        assert headers["Authorization"] == ("Bearer fake-service-token")

        assert headers["Accept"] == "application/json"

        assert params == {"max": 20, "search": "e1004"}

        assert timeout == 5

        return fake_response

    monkeypatch.setattr(
        admin_service.requests,
        "get",
        fake_get,
    )

    users = admin_service.search_users(
        admin_api_url=("https://keycloak.test/admin/realms/novasecure"),
        token_url="https://keycloak.test/token",
        client_id="iam-governance-service",
        client_secret="fake-secret",
        search="e1004",
    )

    assert len(users) == 1

    assert users[0]["username"] == "e1004"


def test_get_user(monkeypatch: MonkeyPatch):
    """
    Verify that a user lookup returns the requested Keycloak account details.
    """

    # We do not want this unit test contacting
    # the real Keycloak token endpoint
    monkeypatch.setattr(
        admin_service, "get_service_access_token", lambda **kwargs: "fake-service-token"
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
            "https://keycloak.test/admin/realms/" "novasecure/users/user-123"
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

    user = admin_service.get_user(
        admin_api_url=("https://keycloak.test/admin/realms/novasecure"),
        token_url="https://keycloak.test/token",
        client_id="iam-governance-service",
        client_secret="fake-secret",
        user_id="user-123",
    )

    assert user["username"] == "e1004"


def test_get_user_groups_paginates(monkeypatch: MonkeyPatch):
    """
    Verify that user-group retrieval paginates through every page and preserves ordering.
    """

    get_service_access_token = Mock(return_value="fake-service-token")
    monkeypatch.setattr(
        admin_service,
        "get_service_access_token",
        get_service_access_token,
    )

    pages = [
        [
            {"id": "group-123", "name": "IAM Operators"},
            {"id": "group-456", "name": "Security Reviewers"},
        ],
        [{"id": "group-789", "name": "Application Owners"}],
        [],
    ]
    offsets = []

    def fake_get(url, headers, timeout, params):
        assert url == (
            "https://keycloak.test/admin/realms/" "novasecure/users/user-123/groups"
        )

        assert headers["Authorization"] == ("Bearer fake-service-token")

        assert headers["Accept"] == "application/json"

        assert timeout == 5

        assert params["max"] == 100

        offsets.append(params["first"])
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = pages[len(offsets) - 1]
        return response

    monkeypatch.setattr(
        admin_service.requests,
        "get",
        fake_get,
    )

    groups = admin_service.get_user_groups(
        admin_api_url=("https://keycloak.test/admin/realms/novasecure"),
        token_url="https://keycloak.test/token",
        client_id="iam-governance-service",
        client_secret="fake-secret",
        user_id="user-123",
    )

    assert len(groups) == 3
    assert [group["id"] for group in groups] == [
        "group-123",
        "group-456",
        "group-789",
    ]
    assert offsets == [0, 2, 3]
    get_service_access_token.assert_called_once_with(
        token_url="https://keycloak.test/token",
        client_id="iam-governance-service",
        client_secret="fake-secret",
    )


def test_get_user_groups_propagates_later_page_failure(monkeypatch):
    """
    Verify that a later page failure raises an error instead of returning partial groups.
    """
    monkeypatch.setattr(
        admin_service,
        "get_service_access_token",
        Mock(return_value="fake-service-token"),
    )

    first_response = Mock()
    first_response.raise_for_status.return_value = None
    first_response.json.return_value = [
        {"id": "group-123", "name": "IAM Operators"},
    ]

    get_mock = Mock(
        side_effect=[
            first_response,
            requests.RequestException("page failed"),
        ]
    )
    monkeypatch.setattr(admin_service.requests, "get", get_mock)

    with pytest.raises(
        KeycloakAdminAPIError,
        match="User groups retrieval failed",
    ):
        admin_service.get_user_groups(
            admin_api_url="https://keycloak.test/admin/realms/novasecure",
            token_url="https://keycloak.test/token",
            client_id="iam-governance-service",
            client_secret="fake-secret",
            user_id="user-123",
        )

    assert get_mock.call_count == 2


@pytest.mark.parametrize("payload", [{}, ["not-a-group"], [None]])
def test_get_user_groups_rejects_invalid_page(monkeypatch, payload):
    """
    Verify that malformed group pages raise a Keycloak API error.
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
        match="Unexpected user groups response",
    ):
        admin_service.get_user_groups(
            admin_api_url="https://keycloak.test/admin/realms/novasecure",
            token_url="https://keycloak.test/token",
            client_id="iam-governance-service",
            client_secret="fake-secret",
            user_id="user-123",
        )
