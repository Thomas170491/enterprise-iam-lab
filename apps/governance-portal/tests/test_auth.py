from flask import redirect
from extensions import oauth

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

    - create the application user
    - store identity data in the session
    - authenticate the user with Flask-Login
    - redirect to the Governance dashboard
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

    monkeypatch.setattr(
        oauth.keycloak,
        "authorize_access_token",
        lambda: fake_token,
    )

    response = client.get(
        "/auth/callback",
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")

    with client.session_transaction() as sess:
        user = sess["user"]

        assert user["sub"] == "test-leo-sub"
        assert user["username"] == "e1004"
        assert user["name"] == "Leo Bernard"
        assert user["email"] == "leo@example.test"

        # We haven't implemented real role extraction yet.
        assert user["client_roles"] == []
        assert user["realm_roles"] == []

        # Flask-Login should also have authenticated
        # the same Keycloak subject.
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

    monkeypatch.setattr(
        oauth.keycloak,
        "authorize_access_token",
        lambda: fake_token,
    )

    response = client.get(
        "/auth/callback",
        follow_redirects=True,
    )

    assert response.status_code == 200

    assert b"Leo Bernard" in response.data
    assert b"e1004" in response.data




