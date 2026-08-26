from unittest.mock import Mock

import services.keycloak_admin_service as admin_service

def test_search_users(monkeypatch):

    #We do not want this unit test catching the real Keycloak token endpoint
    monkeypatch.setattr(
        admin_service,
        "get_service_access_token",
        lambda **kwagrs : "fake-service-token"
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
        assert url == "https://keycloak.test/admin/realms/novasecure/users"

        assert headers["Authorization"] == "Bearer fake-service-token"

        assert headers["Accept"] == "application/json"

        assert params == {
            "max" : 20,
            "search" : "e1004"
        }

        assert timeout == 5

        return fake_response 

    monkeypatch.setattr(
        admin_service.requests,
        "get",
        fake_get,

    )

    users = admin_service.search_users(
        admin_api_url= "https://keycloak.test/admin/realms/novasecure",
        token_url= "https://keycloak.test/token",
        client_id= "iam-governence-service",
        client_secret="fake-secret",
        search="e1004"
    )
    
    assert len(users) == 1

    assert users[0]["username"] == "e1004"

def test_get_user(monkeypatch):

    #We do not want this unit test catching the real Keycloak token endpoint
    monkeypatch.setattr(
        admin_service,
        "get_service_access_token",
        lambda **kwagrs : "fake-service-token"
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
        assert url == "https://keycloak.test/admin/realms/novasecure/users/user-123"

        assert headers["Authorization"] == "Bearer fake-service-token"

        assert headers["Accept"] == "application/json"

        assert timeout == 5

        return fake_response 

    monkeypatch.setattr(
        admin_service.requests,
        "get",
        fake_get,

    )

    user = admin_service.get_user(
        admin_api_url= "https://keycloak.test/admin/realms/novasecure",
        token_url= "https://keycloak.test/token",
        client_id= "iam-governence-service",
        client_secret="fake-secret",
        user_id="user-123"
    )
    
    assert user["username"] == "e1004"

def test_get_user_groups(monkeypatch):

    #We do not want this unit test catching the real Keycloak token endpoint
    monkeypatch.setattr(
        admin_service,
        "get_service_access_token",
        lambda **kwagrs : "fake-service-token"
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
        assert url == "https://keycloak.test/admin/realms/novasecure/users/user-123/groups"

        assert headers["Authorization"] == "Bearer fake-service-token"

        assert headers["Accept"] == "application/json"

        assert timeout == 5

        return fake_response 

    monkeypatch.setattr(
        admin_service.requests,
        "get",
        fake_get,

    )

    groups = admin_service.get_user_groups(
        admin_api_url= "https://keycloak.test/admin/realms/novasecure",
        token_url= "https://keycloak.test/token",
        client_id= "iam-governence-service",
        client_secret="fake-secret",
        user_id="user-123"
    )
    
    assert len(groups) == 1

    assert groups[0]["name"] == "IAM Operators"

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
        {"name": "priviledged-user"},
    ]

    monkeypatch.setattr(
        admin_service.requests,
        "get",
        lambda *args, **kwargs: fake_response,
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