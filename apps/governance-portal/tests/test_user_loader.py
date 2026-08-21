from flask import session

from extensions import login_manager


def test_user_loader_reconstructs_user(app):
    """
    Flask-Login should reconstruct the User object
    from our server-side identity session.
    """

    with app.test_request_context("/"):
        session["user"] = {
            "sub": "subject-123",
            "username": "e1004",
            "name": "Leo Bernard",
            "email": "leo@example.test",
            "client_roles": [
                "identity-viewer",
            ],
            "realm_roles": [
                "privileged-user",
            ],
        }

        user = login_manager._user_callback(
            "subject-123"
        )

        assert user is not None

        assert user.sub == "subject-123"
        assert user.id == "subject-123"
        assert user.username == "e1004"
        assert user.name == "Leo Bernard"
        assert user.email == "leo@example.test"

        assert user.client_roles == [
            "identity-viewer"
        ]

        assert user.realm_roles == [
            "privileged-user"
        ]


def test_user_loader_rejects_identity_mismatch(
    app,
):
    """
    Flask-Login's user ID must match the Keycloak
    subject stored in our application session.

    A mismatch must invalidate the session.
    """

    with app.test_request_context("/"):
        session["user"] = {
            "sub": "subject-A",
            "username": "e1004",
            "name": "Leo Bernard",
            "email": "leo@example.test",
            "client_roles": [],
            "realm_roles": [],
        }

        user = login_manager._user_callback(
            "subject-B"
        )

        assert user is None

        assert "user" not in session


def test_user_loader_handles_missing_session(
    app,
):
    """
    Missing authentication state should produce an
    anonymous user instead of raising an exception.
    """

    with app.test_request_context("/"):
        user = login_manager._user_callback(
            "subject-123"
        )

        assert user is None