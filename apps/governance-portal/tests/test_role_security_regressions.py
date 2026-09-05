from unittest.mock import ANY, Mock

import services.role_service as role_service

import governance.routes as governance_routes


from auth.permissions import (
    ACCESS_REVIEWER,
    IDENTITY_VIEWER,
    ROLE_MANAGER,
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

def test_forged_unmanaged_role_assignement_is_blocked(client,monkeypatch):
    _login_user(client, client_roles=[ROLE_MANAGER])

    fake_client_lookup = Mock()

    monkeypatch.setattr(
        role_service,
        "get_client_uuid",
        fake_client_lookup
    )
    response = client.post(
        "/identities/user-123/roles",
        data={
            "role_name": "portal-user",
        },
    )

    assert response.status_code == 403
    fake_client_lookup.assert_not_called()


def test_forged_unmanaged_role_removal_is_blocked(client,monkeypatch):
    _login_user(client, client_roles=[ROLE_MANAGER])

    fake_client_lookup = Mock()

    monkeypatch.setattr(
        role_service,
        "get_client_uuid",
        fake_client_lookup
    )
    response = client.post(
        "/identities/user-123/roles/portal-user/remove",
    )

    assert response.status_code == 403
    fake_client_lookup.assert_not_called()

def test_identity_viewer_cannot_forge_role_removal(
    client,
    monkeypatch,
):
    _login_user(client, client_roles=[IDENTITY_VIEWER])

    fake_remove = Mock()

    monkeypatch.setattr(
        governance_routes,
        "remove_identity_client_role",
        fake_remove
    )

    response = client.post(
        "/identities/user-123/roles/finance-data-viewer/remove",
    )

    assert response.status_code == 403
    fake_remove.assert_not_called()

def test_access_reviewer_cannot_forge_role_removal(
    client,
    monkeypatch,
):
    _login_user(
        client,
        [ACCESS_REVIEWER],
    )

    fake_remove = Mock()

    monkeypatch.setattr(
        governance_routes,
        "remove_identity_client_role",
        fake_remove,
    )

    response = client.post(
        "/identities/user-123/roles/finance-data-viewer/remove",
    )
    assert response.status_code == 403
    fake_remove.assert_not_called()

def test_role_removal_rejects_missing_csrf_token(
    app,
    client,
    monkeypatch,
):
    _login_user(client, client_roles=[ROLE_MANAGER])

    fake_remove = Mock()

    app.config["WTF_CSRF_ENABLED"] = True

    monkeypatch.setattr(
        governance_routes,
        "remove_identity_client_role",
        fake_remove,
    )

    response = client.post(
        "/identities/user-123/roles/finance-data-viewer/remove",
       
    )

    assert response.status_code == 400
    fake_remove.assert_not_called()

def test_role_removal_rejects_missing_csrf_token(
    app,
    client,
    monkeypatch,
):
    # CSRF is disabled globally in the normal test fixture,
    # so explicitly enable it for this security regression.
    app.config["WTF_CSRF_ENABLED"] = True

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

    # Deliberately submit the POST without a csrf_token.
    response = client.post(
        (
            "/identities/user-123/roles/"
            "finance-data-viewer/remove"
        ),
    )

    # Flask-WTF must reject the request before the
    # privileged mutation service is reached.
    assert response.status_code == 400
    fake_remove.assert_not_called()

def test_role_assignment_cannot_override_governed_client(
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

            # Attacker tries to make the route modify a
            # different Keycloak client.
            "target_client_name": "iam-admin-portal",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302

    # The forged form value must have no influence.
    # The server chooses the governed client itself.
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