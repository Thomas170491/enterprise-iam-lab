import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

#Load Governance Portal-specific environment variables
load_dotenv(BASE_DIR/".env")

class Config :

    # ========================================================
    # FLASK
    # ========================================================

    SECRET_KEY = os.getenv("FLASK_SECRET_KEY")
    SESSION_TYPE = 'filesystem'
    SESSION_COOKIE_HTTP_ONLY = True
    SESSION_COOKIE_SAMESITE ='Lax'


    # Local development currently uses HTTP.
    # This becomes True when we move the application to HTTPS.
    SESSION_COOKIE_SECURE = False

    SESSION_COOKIE_NAME = "novasecure_governance_session"

    



    # ========================================================
    # FLASK-SMOREST / OPENAPI
    # =======================================================

    API_TITLE = "NovaSecure IAM Governance API"

    API_VERSION = "v1"

    OPENAPI_VERSION = "3.0.3"
    
    OPENAPI_URL_PREFIX = "/api"

    OPENAPI_JSON_PATH = "openapi.json"


    # --------------------------------------------------
    # Keycloak / OIDC
    # --------------------------------------------------

    KEYCLOAK_SERVER_URL = os.getenv(
        "KEYCLOAK_SERVER_URL",
        "http://localhost:8080",
    )

    KEYCLOAK_REALM = os.getenv(
        "KEYCLOAK_REALM",
        "novasecure",
    )

    KEYCLOAK_CLIENT_ID = os.getenv(
        "KEYCLOAK_CLIENT_ID",
        "iam-admin-portal",
    )

    KEYCLOAK_CLIENT_SECRET = os.getenv(
        "KEYCLOAK_CLIENT_SECRET"
    )

    KEYCLOAK_METADATA_URL = (
        f"{KEYCLOAK_SERVER_URL}"
        f"/realms/{KEYCLOAK_REALM}"
        "/.well-known/openid-configuration"
    )

#Fail immediately if required configuration is missing
if not Config.SECRET_KEY :
    raise RuntimeError("FLASK_SECRET_KEY cannot be empty")

if not Config.KEYCLOAK_CLIENT_SECRET :
    raise RuntimeError("KEYCLOAK_CLIENT_SECRET cannot be enpty")


    