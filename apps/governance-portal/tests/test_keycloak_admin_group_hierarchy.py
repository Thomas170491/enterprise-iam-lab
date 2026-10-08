from unittest.mock import Mock

import pytest
import requests

import services.keycloak_admin_service as admin_service

from services.exceptions import KeycloakAdminAPIError


def test_get_group_returns_details(monkeypatch):
    """
    Verify that group details are retrieved and returned unchanged.
    """

    monkeypatch.setattr(
        admin_service,
        "get_service_access_token",
        lambda **kwargs: "fake-service-token",
    )

    payload = {
        "id": "group-123",
        "name": "Finance",
        "path": "/departments/Finance",
        "parentId": "parent-456",
    }

    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = payload

    def fake_get(url, headers, timeout):
        assert url == ("https://keycloak.test/admin/realms/novasecure/groups/group-123")
        assert headers["Authorization"] == "Bearer fake-service-token"
        assert headers["Accept"] == "application/json"
        assert timeout == 5
        return response

    monkeypatch.setattr(admin_service.requests, "get", fake_get)

    group = admin_service.get_group(
        admin_api_url="https://keycloak.test/admin/realms/novasecure",
        token_url="https://keycloak.test/token",
        client_id="iam-governance-service",
        client_secret="fake-secret",
        group_id="group-123",
    )

    assert group == payload
    response.json.assert_called_once()


def test_get_group_rejects_invalid_json(monkeypatch):
    """
    Verify that invalid group JSON raises a Keycloak Admin API error.
    """

    monkeypatch.setattr(
        admin_service,
        "get_service_access_token",
        lambda **kwargs: "fake-service-token",
    )

    response = Mock()
    response.raise_for_status.return_value = None
    response.json.side_effect = ValueError("invalid JSON")

    monkeypatch.setattr(admin_service.requests, "get", Mock(return_value=response))

    with pytest.raises(
        KeycloakAdminAPIError,
        match="Invalid JSON response",
    ):
        admin_service.get_group(
            admin_api_url="https://keycloak.test/admin/realms/novasecure",
            token_url="https://keycloak.test/token",
            client_id="iam-governance-service",
            client_secret="fake-secret",
            group_id="group-123",
        )


@pytest.mark.parametrize("payload", [[], "invalid", None])
def test_get_group_rejects_invalid_structure(monkeypatch, payload):
    """
    Verify that group details must be a dictionary.
    """

    monkeypatch.setattr(
        admin_service,
        "get_service_access_token",
        lambda **kwargs: "fake-service-token",
    )

    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = payload
    monkeypatch.setattr(admin_service.requests, "get", Mock(return_value=response))

    with pytest.raises(
        KeycloakAdminAPIError,
        match="Unexpected group response",
    ):
        admin_service.get_group(
            admin_api_url="https://keycloak.test/admin/realms/novasecure",
            token_url="https://keycloak.test/token",
            client_id="iam-governance-service",
            client_secret="fake-secret",
            group_id="group-123",
        )


def test_get_group_propagates_request_failure(monkeypatch):
    """
    Verify that a failed group lookup raises a Keycloak Admin API error.
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
        match="Group retrieval failed",
    ):
        admin_service.get_group(
            admin_api_url="https://keycloak.test/admin/realms/novasecure",
            token_url="https://keycloak.test/token",
            client_id="iam-governance-service",
            client_secret="fake-secret",
            group_id="group-123",
        )

    response.json.assert_not_called()


def test_get_group_ancestors_returns_nearest_parent_first(monkeypatch):
    """
    Verify that group ancestors are returned from the nearest parent to the root.
    """

    groups = {
        "finance-team-id": {
            "id": "finance-team-id",
            "name": "Finance Team",
            "parentId": "finance-id",
        },
        "finance-id": {
            "id": "finance-id",
            "name": "Finance",
            "parentId": "departments-id",
        },
        "departments-id": {
            "id": "departments-id",
            "name": "Departments",
            "parentId": "root-id",
        },
        "root-id": {
            "id": "root-id",
            "name": "root",
        },
    }

    def fake_get_group(**kwargs):
        return groups[kwargs["group_id"]]

    get_group_mock = Mock(side_effect=fake_get_group)
    monkeypatch.setattr(admin_service, "get_group", get_group_mock)

    ancestors = admin_service.get_group_ancestors(
        admin_api_url="https://keycloak.test/admin/realms/novasecure",
        token_url="https://keycloak.test/token",
        client_id="iam-governance-service",
        client_secret="fake-secret",
        group_id="finance-team-id",
    )

    assert len(ancestors) == 3
    assert [group["id"] for group in ancestors] == [
        "finance-id",
        "departments-id",
        "root-id",
    ]
    assert [group["name"] for group in ancestors] == [
        "Finance",
        "Departments",
        "root",
    ]
    assert get_group_mock.call_args_list == [
        (
            (),
            {
                "admin_api_url": "https://keycloak.test/admin/realms/novasecure",
                "token_url": "https://keycloak.test/token",
                "client_id": "iam-governance-service",
                "client_secret": "fake-secret",
                "group_id": "finance-team-id",
            },
        ),
        (
            (),
            {
                "admin_api_url": "https://keycloak.test/admin/realms/novasecure",
                "token_url": "https://keycloak.test/token",
                "client_id": "iam-governance-service",
                "client_secret": "fake-secret",
                "group_id": "finance-id",
            },
        ),
        (
            (),
            {
                "admin_api_url": "https://keycloak.test/admin/realms/novasecure",
                "token_url": "https://keycloak.test/token",
                "client_id": "iam-governance-service",
                "client_secret": "fake-secret",
                "group_id": "departments-id",
            },
        ),
        (
            (),
            {
                "admin_api_url": "https://keycloak.test/admin/realms/novasecure",
                "token_url": "https://keycloak.test/token",
                "client_id": "iam-governance-service",
                "client_secret": "fake-secret",
                "group_id": "root-id",
            },
        ),
    ]


def test_get_group_ancestors_returns_empty_list_for_root_group(monkeypatch):
    """
    Verify that a root group with no parent returns an empty ancestor list.
    """

    get_group_mock = Mock(
        return_value={
            "id": "root-id",
            "name": "root",
        }
    )
    monkeypatch.setattr(admin_service, "get_group", get_group_mock)

    ancestors = admin_service.get_group_ancestors(
        admin_api_url="https://keycloak.test/admin/realms/novasecure",
        token_url="https://keycloak.test/token",
        client_id="iam-governance-service",
        client_secret="fake-secret",
        group_id="root-id",
    )

    assert ancestors == []
    get_group_mock.assert_called_once_with(
        admin_api_url="https://keycloak.test/admin/realms/novasecure",
        token_url="https://keycloak.test/token",
        client_id="iam-governance-service",
        client_secret="fake-secret",
        group_id="root-id",
    )


@pytest.mark.parametrize("invalid_parent_id", ["", "   ", 123])
def test_get_group_ancestors_rejects_invalid_parent_id(monkeypatch, invalid_parent_id):
    """
    Verify that invalid parent group identifiers are rejected before further lookup.
    """

    get_group_mock = Mock(
        return_value={
            "id": "finance-team-id",
            "name": "Finance Team",
            "parentId": invalid_parent_id,
        }
    )
    monkeypatch.setattr(admin_service, "get_group", get_group_mock)

    with pytest.raises(
        KeycloakAdminAPIError,
        match="Invalid parent group ID",
    ):
        admin_service.get_group_ancestors(
            admin_api_url="https://keycloak.test/admin/realms/novasecure",
            token_url="https://keycloak.test/token",
            client_id="iam-governance-service",
            client_secret="fake-secret",
            group_id="finance-team-id",
        )

    get_group_mock.assert_called_once_with(
        admin_api_url="https://keycloak.test/admin/realms/novasecure",
        token_url="https://keycloak.test/token",
        client_id="iam-governance-service",
        client_secret="fake-secret",
        group_id="finance-team-id",
    )


def test_get_group_ancestors_rejects_group_hierarchy_cycle(monkeypatch):
    """
    Verify that a cyclic group hierarchy is rejected before a group is revisited.
    """

    groups = {
        "finance-team-id": {
            "id": "finance-team-id",
            "name": "Finance Team",
            "parentId": "finance-id",
        },
        "finance-id": {
            "id": "finance-id",
            "name": "Finance",
            "parentId": "finance-team-id",
        },
    }

    def fake_get_group(**kwargs):

        return groups[kwargs["group_id"]]

    get_group_mock = Mock(side_effect=fake_get_group)
    monkeypatch.setattr(admin_service, "get_group", get_group_mock)

    with pytest.raises(
        KeycloakAdminAPIError,
        match="Group hierarchy cycle detected",
    ):
        admin_service.get_group_ancestors(
            admin_api_url="https://keycloak.test/admin/realms/novasecure",
            token_url="https://keycloak.test/token",
            client_id="iam-governance-service",
            client_secret="fake-secret",
            group_id="finance-team-id",
        )

    assert [call.kwargs["group_id"] for call in get_group_mock.call_args_list] == [
        "finance-team-id",
        "finance-id",
    ]


def test_get_group_ancestors_propagates_parent_lookup_failure(monkeypatch):
    """
    Verify that a parent group lookup failure propagates unchanged.
    """

    def fake_get_group(**kwargs):
        """
        Return the starting group, then simulate a failed parent lookup.
        """
        group_id = kwargs["group_id"]

        if group_id == "finance-team-id":
            return {
                "id": "finance-team-id",
                "name": "Finance Team",
                "parentId": "finance-id",
            }

        raise KeycloakAdminAPIError("Group retrieval failed")

    get_group_mock = Mock(side_effect=fake_get_group)
    monkeypatch.setattr(admin_service, "get_group", get_group_mock)

    with pytest.raises(
        KeycloakAdminAPIError,
        match="Group retrieval failed",
    ):
        admin_service.get_group_ancestors(
            admin_api_url="https://keycloak.test/admin/realms/novasecure",
            token_url="https://keycloak.test/token",
            client_id="iam-governance-service",
            client_secret="fake-secret",
            group_id="finance-team-id",
        )

    assert [call.kwargs["group_id"] for call in get_group_mock.call_args_list] == [
        "finance-team-id",
        "finance-id",
    ]


def test_get_user_groups_with_ancestors_includes_parent(monkeypatch):
    """
    Verify that a user's group memberships include their ancestor groups.
    """

    fake_get_user_groups = Mock(
        return_value=[
            {
                "id": "finance-team-id",
                "name": "Finance Team",
                "parentId": "finance-id",
            }
        ]
    )

    fake_get_group_ancestors = Mock(
        return_value=[
            {
                "id": "finance-id",
                "name": "Finance",
                "parentId": "Root",
            }
        ]
    )

    monkeypatch.setattr(admin_service, "get_user_groups", fake_get_user_groups)

    monkeypatch.setattr(admin_service, "get_group_ancestors", fake_get_group_ancestors)

    groups = admin_service.get_user_groups_with_ancestors(
        admin_api_url="https://keycloak.test/admin/realms/novasecure",
        token_url="https://keycloak.test/token",
        client_id="iam-governance-service",
        client_secret="fake-secret",
        user_id="user-123",
    )
    assert [group["id"] for group in groups] == ["finance-team-id", "finance-id"]


@pytest.mark.parametrize("group_id", [None, "", "   "])
def test_get_user_groups_with_ancestors_rejects_invalid_membership_id(
    monkeypatch, group_id
):
    """
    Verify that invalid membership IDs stop ancestry lookup.
    """
    fake_get_user_groups = Mock(
        return_value=[
            {
                "id": group_id,
                "name": "Invalid Finance Group",
            }
        ]
    )
    fake_get_group_ancestors = Mock(return_value=[])

    monkeypatch.setattr(
        admin_service,
        "get_user_groups",
        fake_get_user_groups,
    )
    monkeypatch.setattr(
        admin_service,
        "get_group_ancestors",
        fake_get_group_ancestors,
    )

    with pytest.raises(
        KeycloakAdminAPIError,
        match="Invalid user group ID",
    ):
        admin_service.get_user_groups_with_ancestors(
            admin_api_url="https://keycloak.test/admin/realms/novasecure",
            token_url="https://keycloak.test/token",
            client_id="iam-governance-service",
            client_secret="fake-secret",
            user_id="user-123",
        )

    fake_get_group_ancestors.assert_not_called()


def test_get_user_groups_with_ancestors_deduplicates_shared_parent(monkeypatch):
    """
    Verify that sibling memberships include their shared parent only once.
    """
    fake_get_user_groups = Mock(
        return_value=[
            {
                "id": "team-a-id",
                "name": "Finance Team A",
                "parentId": "finance-id",
            },
            {
                "id": "team-b-id",
                "name": "Finance Team B",
                "parentId": "finance-id",
            },
        ]
    )
    fake_get_group_ancestors = Mock(
        return_value=[
            {
                "id": "finance-id",
                "name": "Finance",
            }
        ]
    )

    monkeypatch.setattr(
        admin_service,
        "get_user_groups",
        fake_get_user_groups,
    )
    monkeypatch.setattr(
        admin_service,
        "get_group_ancestors",
        fake_get_group_ancestors,
    )

    groups = admin_service.get_user_groups_with_ancestors(
        admin_api_url="https://keycloak.test/admin/realms/novasecure",
        token_url="https://keycloak.test/token",
        client_id="iam-governance-service",
        client_secret="fake-secret",
        user_id="user-123",
    )

    assert [group["id"] for group in groups] == [
        "team-a-id",
        "finance-id",
        "team-b-id",
    ]


@pytest.mark.parametrize("ancestor_id", [None, "", "   "])
def test_get_user_groups_with_ancestors_rejects_invalid_ancestor_id(
    monkeypatch, ancestor_id
):
    """Verify that invalid ancestor IDs prevent returning a group hierarchy."""
    fake_get_user_groups = Mock(
        return_value=[
            {
                "id": "finance-team-id",
                "name": "Finance Team",
                "parentId": "finance-id",
            }
        ]
    )
    fake_get_group_ancestors = Mock(
        return_value=[
            {
                "id": ancestor_id,
                "name": "Finance",
                "parentId": None,
            }
        ]
    )

    monkeypatch.setattr(admin_service, "get_user_groups", fake_get_user_groups)
    monkeypatch.setattr(admin_service, "get_group_ancestors", fake_get_group_ancestors)

    with pytest.raises(
        KeycloakAdminAPIError,
        match="Invalid ancestor group ID",
    ):
        admin_service.get_user_groups_with_ancestors(
            admin_api_url="https://keycloak.test/admin/realms/novasecure",
            token_url="https://keycloak.test/token",
            client_id="iam-governance-service",
            client_secret="fake-secret",
            user_id="user-123",
        )

    assert fake_get_group_ancestors.call_args.kwargs["group_id"] == ("finance-team-id")
