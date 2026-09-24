from unittest.mock import Mock

from pytest import MonkeyPatch

import pytest
import requests

import services.keycloak_admin_service as admin_service

from services.exceptions import KeycloakAdminAPIError


def test_search_users(monkeypatch: MonkeyPatch):

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
        lambda **kwargs : "fake-service-token",
    )

    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = payload
    monkeypatch.setattr(
        admin_service.requests, 
        "get",
        lambda *args, **kwargs: response
    )

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


def test_get_group_role_mappings_returns_mappings(monkeypatch):
    """
    Verify that group role mappings are retrieved and returned unchanged.
    """
    monkeypatch.setattr(
        admin_service,
        "get_service_access_token",
        lambda **kwargs : "fake-service-token"
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

    monkeypatch.setattr(
        admin_service.requests, 
        "get", 
        fake_get)

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
        admin_service,
        "get_service_access_token",
        lambda **kwargs : "fake-service-token"
    )

    response = Mock()
    response.raise_for_status.return_value = None
    response.json.side_effect = ValueError("invalid JSON")
    monkeypatch.setattr(
        admin_service.requests, 
        "get", 
        lambda *args, **kwargs: response
    )

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
        lambda **kwargs : "fake-service-token",
    )

    response = Mock()
    response.raise_for_status.side_effect = requests.HTTPError("403 Forbidden")
    monkeypatch.setattr(
        admin_service.requests, 
        "get", 
        lambda *args, **kwargs: response
    )

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
        lambda **kwargs : "fake-service-token",
    )

    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = payload
    monkeypatch.setattr(
        admin_service.requests,
        "get", 
        lambda *args, **kwargs: response
    )

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


def test_get_group_returns_details(monkeypatch):
    """
    Verify that group details are retrieved and returned unchanged.
    """

    monkeypatch.setattr(
        admin_service,
        "get_service_access_token",
        lambda **kwargs : "fake-service-token",
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

    monkeypatch.setattr(
        admin_service.requests, 
        "get", 
        fake_get
    )

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
        lambda **kwargs : "fake-service-token",
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
        lambda **kwargs : "fake-service-token",
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
        lambda **kwargs : "fake-service-token",
    )

    response = Mock()
    response.raise_for_status.side_effect = requests.HTTPError("403 Forbidden")
    
    monkeypatch.setattr(
        admin_service.requests, 
        "get", 
        lambda *args, **kwargs : response
    )

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
    monkeypatch.setattr(
        admin_service, 
        "get_group", 
        get_group_mock)

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
def test_get_group_ancestors_rejects_invalid_parent_id(monkeypatch,invalid_parent_id):
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

    get_group_mock = Mock(side_effect= fake_get_group)
    monkeypatch.setattr(
        admin_service,
        "get_group",
        get_group_mock
    )

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
    
    fake_get_user_groups = Mock(return_value=
        [
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
    
    monkeypatch.setattr(
        admin_service,
        "get_user_groups",
        fake_get_user_groups
    )
    
    monkeypatch.setattr(
        admin_service,
        "get_group_ancestors",
        fake_get_group_ancestors
    )
    
    groups= admin_service.get_user_groups_with_ancestors(
                admin_api_url="https://keycloak.test/admin/realms/novasecure",
                token_url="https://keycloak.test/token",
                client_id="iam-governance-service",
                client_secret="fake-secret",
                user_id="user-123",
            )
    assert [group["id"] for group in groups] == ["finance-team-id","finance-id"]


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
    monkeypatch.setattr(
        admin_service, "get_group_ancestors", fake_get_group_ancestors
    )

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

    assert fake_get_group_ancestors.call_args.kwargs["group_id"] == (
        "finance-team-id"
    )


def test_get_effective_realm_roles(monkeypatch):
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
        admin_service,
        "get_service_access_token",
        lambda **kwargs : "fake-service-token" 
    )
    
    fake_response = Mock()
    
    fake_response.raise_for_status.return_value = None
    
    fake_response.json.return_value = [
            {
                "name": "finance-data-viewer",
                "id" : "role-id-1"
            },
    
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
        group_id= "group-123",
        target_client_name = "employee-portal"
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
        admin_service,
        "get_service_access_token",
        lambda **kwargs : "fake-service-token" 
    )
    
    fake_response = Mock()
        
    fake_response.raise_for_status.side_effect =  admin_service.requests.HTTPError(
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
        
    monkeypatch.setattr(
        admin_service.requests,
        "get",
        fake_get
    )

    with pytest.raises(KeycloakAdminAPIError, match="Group effective client roles retrieval failed"):
        admin_service.get_group_effective_client_roles(
            admin_api_url=("https://keycloak.test/admin/realms/novasecure"),
            token_url="https://keycloak.test/token",
            client_id="iam-governance-service",
            client_secret="fake-secret",
            group_id= "group-123",
            target_client_name = "employee-portal"
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
        admin_service,
        "get_service_access_token",
        lambda **kwargs : "fake-service-token" 
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
    
    monkeypatch.setattr(
        admin_service.requests,
        "get",
        fake_get
    )
    
    with pytest.raises(KeycloakAdminAPIError, match= "Invalid JSON response") :
        admin_service.get_group_effective_client_roles(
            admin_api_url=("https://keycloak.test/admin/realms/novasecure"),
            token_url="https://keycloak.test/token",
            client_id="iam-governance-service",
            client_secret="fake-secret",
            group_id= "group-123",
            target_client_name = "employee-portal"
        )
@pytest.mark.parametrize("payload", [{"id": "role-id-1"}, ["not-a-role-object"]])
def test_get_group_effective_client_roles_rejects_invalid_structure(monkeypatch, payload):
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
        admin_service,
        "get_service_access_token",
        lambda **kwargs : "fake-service-token" 
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
    
    monkeypatch.setattr(
        admin_service.requests,
        "get",
        fake_get
    )
    
    with pytest.raises(KeycloakAdminAPIError, match= "Unexpected group effective client role response") :
        admin_service.get_group_effective_client_roles(
            admin_api_url=("https://keycloak.test/admin/realms/novasecure"),
            token_url="https://keycloak.test/token",
            client_id="iam-governance-service",
            client_secret="fake-secret",
            group_id= "group-123",
            target_client_name = "employee-portal"
        )
    
    

def test_get_client_uuid(monkeypatch):
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
