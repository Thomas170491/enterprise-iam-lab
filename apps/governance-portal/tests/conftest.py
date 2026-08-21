import os 
import pytest


# ---------------------------------------------------------
# Test environment
# ---------------------------------------------------------
#
# These values are deliberately fake.
#
# Tests should never depend on the real .env secrets.
# They must also never contain actual Keycloak credentials.
# ---------------------------------------------------------

os.environ["FLASK_SECRET_KEY"] = (
    "test-flask-secret-key-not-for-production"
)

os.environ["KEYCLOAK_CLIENT_SECRET"] = (
    "test-keycloak-client-secret"
)

os.environ["KEYCLOAK_SERVER_URL"] = (
    "http://localhost:8080"
)

os.environ["KEYCLOAK_REALM"] = "novasecure"

os.environ["KEYCLOAK_CLIENT_ID"] = (
    "iam-admin-portal"
)

from app import app as flask_app

@pytest.fixture
def app():
    """
    Provide the Governance Portal application in testing mode
    """

    flask_app.config.update(
        TESTING = True,
        WTF_CSRF_ENABLED = False
    )

    yield flask_app

@pytest.fixture
def client(app):
    """
    Provide a Flask test client
    """
    return app.test_client()


