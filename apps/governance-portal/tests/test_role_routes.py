from unittest.mock import ANY, Mock

import governance.routes as governance_routes

from auth.permissions import (
    ACCESS_REVIEWER,
    IDENTITY_VIEWER,
    ROLE_MANAGER,
)

from services.exceptions import (
    AuditPersistenceError,
    KeycloakAdminAPIError,
)

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


def test_role_manager_can_assign_role(
        client,
        monkeypatch,
):
    _login_user(
        client,
        [ROLE_MANAGER],
    )

    fake_assign = Mock(
        return_value={
            "user_id": "user-123",
            "client_name": "employee-portal",
            "role_id": "role-123",
            "role_name": "finance-data-viewer",
        }
    )

    monkeypatch.setattr(
        governance_routes,
        "assign_identity_client_role",
        fake_assign,
    )

    response = client.post(
        "/identities/user-123/roles",
        data={
            "role_name": "finance-data-viewer",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302

    fake_assign.assert_called_once_with(
        admin_api_url=ANY,
        token_url=ANY,
        client_id=ANY,
        client_secret=ANY,
        user_id="user-123",
        target_client_name="employee-portal",
        role_name="finance-data-viewer",
        actor_user_id="test-subject",
        actor_username="test-user",
    )
def test_role_manager_can_remove_role(
        client,
        monkeypatch,
):
    _login_user(
        client,
        [ROLE_MANAGER],
    )

    fake_remove = Mock()

    monkeypatch.setattr(
        governance_routes,
        "remove_identity_client_role",
        fake_remove,
    )

    response = client.post(
        (
            "/identities/user-123/roles/"
            "finance-data-viewer/remove"
        ),
        follow_redirects=False,
    )

    assert response.status_code == 302

    fake_remove.assert_called_once_with(
        admin_api_url=ANY,
        token_url=ANY,
        client_id=ANY,
        client_secret=ANY,
        user_id="user-123",
        target_client_name="employee-portal",
        role_name="finance-data-viewer",
        actor_user_id="test-subject",
        actor_username="test-user",
    )

def test_identity_viewer_cannot_assign_role(
        client,
        monkeypatch,
):
    _login_user(
        client,
        [IDENTITY_VIEWER],
    )

    fake_assign = Mock()

    monkeypatch.setattr(
        governance_routes,
        "assign_identity_client_role",
        fake_assign,
    )

    response = client.post(
        "/identities/user-123/roles",
        data={
            "role_name": "finance-data-viewer",
        },
    )

    assert response.status_code == 403
    fake_assign.assert_not_called()

def test_access_reviewer_cannot_assign_role(
        client,
        monkeypatch,
):
    _login_user(
        client,
        [ACCESS_REVIEWER],
    )

    fake_assign = Mock()

    monkeypatch.setattr(
        governance_routes,
        "assign_identity_client_role",
        fake_assign,
    )

    response = client.post(
        "/identities/user-123/roles",
        data={
            "role_name": "finance-data-viewer",
        },
    )

    assert response.status_code == 403
    fake_assign.assert_not_called()

def test_role_assignment_requires_login(
        client,
        monkeypatch,
):
    fake_assign = Mock()

    monkeypatch.setattr(
        governance_routes,
        "assign_identity_client_role",
        fake_assign,
    )

    response = client.post(
        "/identities/user-123/roles",
        data={
            "role_name": "finance-data-viewer",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]

    fake_assign.assert_not_called()

def test_role_assignment_requires_login(
        client,
        monkeypatch,
):
    fake_assign = Mock()

    monkeypatch.setattr(
        governance_routes,
        "assign_identity_client_role",
        fake_assign,
    )

    response = client.post(
        "/identities/user-123/roles",
        data={
            "role_name": "finance-data-viewer",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]

    fake_assign.assert_not_called()

def test_role_assignment_returns_503_when_audit_fails(
        client,
        monkeypatch,
):
    _login_user(
        client,
        [ROLE_MANAGER],
    )

    monkeypatch.setattr(
        governance_routes,
        "assign_identity_client_role",
        Mock(
            side_effect=AuditPersistenceError(
                "database unavailable"
            )
        ),
    )

    response = client.post(
        "/identities/user-123/roles",
        data={
            "role_name": "finance-data-viewer",
        },
    )

    assert response.status_code == 503

def test_role_assignment_rejects_missing_csrf_token(
        app,
        client,
        monkeypatch,
):
    app.config["WTF_CSRF_ENABLED"] = True

    _login_user(
        client,
        [ROLE_MANAGER],
    )

    fake_assign = Mock()

    monkeypatch.setattr(
        governance_routes,
        "assign_identity_client_role",
        fake_assign,
    )
    print(app.extensions)
    print(app.config["WTF_CSRF_ENABLED"])
    response = client.post(
        "/identities/user-123/roles",
        data={
            "role_name": "finance-data-viewer",
        },
    )

    assert response.status_code == 400

    # CSRF rejection happens before our mutation route runs.
    fake_assign.assert_not_called()