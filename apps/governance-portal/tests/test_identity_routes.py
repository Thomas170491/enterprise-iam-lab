from pytest import MonkeyPatch

import governance.routes as governance_routes
from unittest.mock import Mock,ANY
from auth.permissions import IDENTITY_VIEWER
from services.exceptions import KeycloakAdminAPIError
import services.identity_service as identity_service 


def _login_user(
    client,
    client_roles,
):
    with client.session_transaction() as sess:
        sess["user"] = {
            "sub": "test-subject",
            "username": "test-user",
            "name": "Test User",
            "email": "test@example.test",
            "client_roles": client_roles,
            "realm_roles": [],
        }

        sess["_user_id"] = "test-subject"
        sess["_fresh"] = True
def test_identity_route_access(
    client,
    monkeypatch,
):
    _login_user(
        client,
        [IDENTITY_VIEWER],
    )

    fake_identities = [
        {
            "id": "user-123",
            "username": "e1004",
            "first_name": "Leo",
            "last_name": "Bernard",
            "email": "leo@example.test",
            "employee_id": "E1004",
            "employment_status": "active",
            "job_title": "IAM Operator",
            "risk_level": "high",
            "enabled": True,
        }
    ]

    fake_search = Mock(
        return_value=fake_identities
    )

    monkeypatch.setattr(
        governance_routes,
        "search_identities",
        fake_search,
    )

    response = client.get("/identities?search=e1004")

    assert response.status_code == 200

    fake_search.assert_called_once()

    assert b"Leo" in response.data
    assert b"Bernard" in response.data
    assert b"e1004" in response.data

def test_identity_route_access_denied(client):
    _login_user(client, [])

    response = client.get("/identities")
    assert response.status_code == 403
   
def test_identity_search_requires_login(
    client,
):
    response = client.get(
        "/identities",
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]

def test_identity_page_does_not_search_without_query(
    client,
    monkeypatch,
):
    _login_user(
        client,
        [IDENTITY_VIEWER],
    )

    def fail_if_called(**kwargs):
        raise AssertionError(
            "search_identities should not be called"
        )

    monkeypatch.setattr(
        governance_routes,
        "search_identities",
        fail_if_called,
    )

    response = client.get("/identities")

    assert response.status_code == 200
    assert b"Enter a username" in response.data

def test_identity_page_does_not_search_automatically(
    client,
    monkeypatch,
):
    _login_user(
        client,
        [IDENTITY_VIEWER],
    )

    fake_search = Mock()

    monkeypatch.setattr(
        governance_routes,
        "search_identities",
        fake_search,
    )

    response = client.get("/identities")

    assert response.status_code == 200
    fake_search.assert_not_called()

    assert b"Enter a username" in response.data

def test_empty_search_returns_all_identities(
    client,
    monkeypatch,
):
    _login_user(
        client,
        [IDENTITY_VIEWER],
    )

    fake_identities = [
        {"username": "e1001"},
        {"username": "e1002"},
        {"username": "e1003"},
        {"username": "e1004"},
        {"username": "e1005"},
    ]

    fake_search = Mock(
        return_value=fake_identities
    )

    monkeypatch.setattr(
        governance_routes,
        "search_identities",
        fake_search,
    )

    response = client.get(
        "/identities?search="
    )

    assert response.status_code == 200
    fake_search.assert_called_once()

    assert b"e1001" in response.data
    assert b"e1005" in response.data


def test_identity_detail_route_access(
    client,
    monkeypatch,
):
    _login_user(
        client,
        [IDENTITY_VIEWER],
    )

    fake_identity_access = {
    "identity": {
        "id": "user-123",
        "username": "e1004",
        "first_name": "Leo",
        "last_name": "Bernard",
        "email": "leo.bernard@novasecure.test",
        "enabled": True,
        "employee_id": "e1004",
        "employment_status": "active",
        "job_title": "IAM Operator",
        "risk_level": "low",
    },
        
        "groups": [
            {
                "id": "group-123",
                "name": "IAM Operators",
            }
        ],
        "realm_roles": [
            {
                "name": "employee",
            }
        ],
        "client_roles": [
            {
                "name": "identity-viewer",
            }
        ],
    }
        
    mock_get_identity_access=Mock(
        return_value=fake_identity_access
    )

    monkeypatch.setattr(
        governance_routes,
        "get_identity_access",
        mock_get_identity_access,
    )
    mock_record_audit_event = Mock(
        return_value=fake_identity_access
    )

    monkeypatch.setattr(
        governance_routes,
        "record_audit_event",
        mock_record_audit_event,
)

    response= client.get(
        "/identities/user-123"
    )

    assert response.status_code == 200
    assert b"Leo" in response.data
    assert b"Bernard" in response.data
    assert b"e1004" in response.data
    mock_get_identity_access.assert_called_once_with(
        admin_api_url= ANY,
        token_url=ANY,
        client_id=ANY,
        client_secret=ANY,
        user_id="user-123",
        target_client_name="iam-admin-portal",
)  
    mock_record_audit_event.assert_called_once_with(
    actor_user_id="test-subject",
    actor_username="test-user",
    action="identity.view",
    target_type="identity",
    target_id="user-123",
    target_name="e1004",
    outcome="success",
    details={
        "source": "governance-portal",
        "service_client": "iam-governance-service",
    },
)    

def test_identity_detail_handles_keycloak_failure(
    client,
    monkeypatch,
):
    _login_user(
        client,
        client_roles=[IDENTITY_VIEWER],
    )

    def fake_get_identity_access(**kwargs):
        raise KeycloakAdminAPIError(
            "User retrieval failed"
        )

    monkeypatch.setattr(
        governance_routes,
        "get_identity_access",
        fake_get_identity_access,
    )

    response = client.get(
        "/identities/user-123"
    )

    assert response.status_code == 502

    assert (
        b"Identity Access Unavailable"
        in response.data
    )

def test_get_identity_access(
     monkeypatch: MonkeyPatch
):
    monkeypatch.setattr(
        identity_service,
        "get_user",
        lambda **kwargs: {
            "id": "user-123",
            "username": "e1004",
            "firstName": "Leo",
            "lastName": "Bernard",
            "email": "leo.bernard@novasecure.test",
            "enabled": True,
            "attributes": {
                "employee_id": ["e1004"],
                "employment_status": ["active"],
                "job_title": ["IAM Operator"],
                "risk_level": ["low"],
            },
        },
    )

    monkeypatch.setattr(
        identity_service,
        "get_user_groups",
        lambda **kwargs: [
            {
                "id": "group-123",
                "name": "IAM Operators",
            }
        ],
    )

    monkeypatch.setattr(
        identity_service,
        "get_effective_realm_roles",
        lambda **kwargs: [
            {
                "name": "employee",
            }
        ],
    )

    monkeypatch.setattr(
        identity_service,
        "get_effective_client_roles",
        lambda **kwargs: [
            {
                "name": "identity-viewer",
            }
        ],
    )

    access = identity_service.get_identity_access(
        admin_api_url=(
            "https://keycloak.test/admin/realms/novasecure"
        ),
        token_url="https://keycloak.test/token",
        client_id="iam-governance-service",
        client_secret="fake-secret",
        user_id="user-123",
        target_client_name="iam-admin-portal",
    )

    assert access["identity"]["username"] == "e1004"

    assert access["identity"]["job_title"] == (
        "IAM Operator"
    )

    assert access["groups"][0]["name"] == (
        "IAM Operators"
    )

    assert access["realm_roles"][0]["name"] == (
        "employee"
    )

    assert access["client_roles"][0]["name"] == (
        "identity-viewer"
    )