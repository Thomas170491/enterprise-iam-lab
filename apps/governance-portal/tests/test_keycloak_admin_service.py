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

    
