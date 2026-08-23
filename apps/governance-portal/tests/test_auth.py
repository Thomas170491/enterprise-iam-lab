from flask import redirect
from extensions import oauth
import auth.routes as auth_routes

def test_login_starts_oidc_flow(client, monkeypatch):
    """
    /login should initiate an OIDC authorization
    request through the Keycloak client.
    """

    def fake_authorize_redirect(redirect_uri):
        assert redirect_uri == (
            "http://localhost/auth/callback"
        )

        return redirect("http://keycloak.test/login")

    monkeypatch.setattr(
        oauth.keycloak,
        "authorize_redirect",
        fake_authorize_redirect
    )

    response = client.get(
        "/login",
        follow_redirects=False
    )

    assert response.status_code == 302

    assert response.headers["Location"] == (
        "http://keycloak.test/login"
    )


def test_oidc_callback_creates_user_session(
    client,
    monkeypatch,
):
    """
    A successful Keycloak callback should:

    - exchange the authorization code
    - validate the access token
    - extract trusted Keycloak roles
    - create the application user
    - store identity + roles in the session
    - authenticate the user with Flask-Login
    """

    fake_userinfo = {
        "sub": "test-leo-sub",
        "preferred_username": "e1004",
        "name": "Leo Bernard",
        "email": "leo@example.test",
    }

    fake_token = {
        "access_token": "fake-access-token",
        "userinfo": fake_userinfo,
    }

    fake_claims = {
        "sub": "test-leo-sub",
        "realm_access": {
            "roles": [
                "employee",
                "privileged-user",
            ]
        },
        "resource_access": {
            "iam-admin-portal": {
                "roles": [
                    "iam-dashboard-access",
                    "identity-viewer",
                    "identity-manager",
                    "role-manager",
                    "report-exporter",
                ]
            }
        },
    }

    # Fake Authlib's token exchange.
    monkeypatch.setattr(
        auth_routes.oauth.keycloak,
        "authorize_access_token",
        lambda: fake_token,
    )

    # Fake cryptographic validation.
    #
    # We test validate_access_token() separately.
    # This callback test only verifies that the route
    # correctly uses its validated output.
    monkeypatch.setattr(
        auth_routes,
        "validate_access_token",
        lambda **kwargs: fake_claims,
    )

    response = client.get(
        "/auth/callback",
        follow_redirects=False,
    )

    assert response.status_code == 302

    with client.session_transaction() as sess:
        user = sess["user"]

        assert user["sub"] == "test-leo-sub"
        assert user["username"] == "e1004"
        assert user["name"] == "Leo Bernard"
        assert user["email"] == "leo@example.test"

        assert user["realm_roles"] == [
            "employee",
            "privileged-user",
        ]

        assert user["client_roles"] == [
            "iam-dashboard-access",
            "identity-viewer",
            "identity-manager",
            "role-manager",
            "report-exporter",
        ]

        assert sess["_user_id"] == "test-leo-sub"

def test_authenticated_user_visible_on_dashboard(
    client,
    monkeypatch,
):
    """
    Complete the mocked login flow and verify that
    current_user is available to the Jinja template.
    """

    fake_token = {
        "access_token": "fake-access-token",
        "userinfo": {
            "sub": "test-leo-sub",
            "preferred_username": "e1004",
            "name": "Leo Bernard",
            "email": "leo@example.test",
        },
    }

    fake_claims = {
        "sub": "test-leo-sub",
        "realm_access": {
            "roles": [
                "employee",
                "privileged-user",
                "iam-dashboard-access"
            ]
        },
        "resource_access": {
        "iam-admin-portal": {
            "roles": [
                "iam-dashboard-access",
                "identity-viewer",
                "identity-manager",
                "role-manager",
                "report-exporter",
            ]
        }
        }
    }

    # Fake Authlib's token exchange.
    monkeypatch.setattr(
        auth_routes.oauth.keycloak,
        "authorize_access_token",
        lambda: fake_token,
    )


    monkeypatch.setattr(
    auth_routes,
    "validate_access_token",
    lambda **kwargs: fake_claims,
)

    

    response = client.get(
        "/auth/callback",
        follow_redirects=True,
    )

    assert response.status_code == 200

    assert b"Leo Bernard" in response.data
    assert b"e1004" in response.data




