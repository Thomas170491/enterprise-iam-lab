from pathlib import Path
import os

from dotenv import load_dotenv;


# Locate and load the .env file from the employee-portal directory
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


class Config:
    # Flask
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY")

    # Keycloak / OIDC
    KEYCLOAK_SERVER_URL = os.getenv("KEYCLOAK_SERVER_URL")
    KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM")
    KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID")
    KEYCLOAK_CLIENT_SECRET = os.getenv("KEYCLOAK_CLIENT_SECRET")

    KEYCLOAK_METADATA_URL = (
        f"{KEYCLOAK_SERVER_URL}/realms/"
        f"{KEYCLOAK_REALM}/.well-known/openid-configuration"
    )

    # Environment
    ENVIRONMENT = os.getenv("FLASK_ENV", "development")

    # Session security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = ENVIRONMENT == "production"

    # Flask-Session
    SESSION_TYPE = "cachelib"


# Validate required configuration
required_config = {
    "FLASK_SECRET_KEY": Config.SECRET_KEY,
    "KEYCLOAK_SERVER_URL": Config.KEYCLOAK_SERVER_URL,
    "KEYCLOAK_REALM": Config.KEYCLOAK_REALM,
    "KEYCLOAK_CLIENT_ID": Config.KEYCLOAK_CLIENT_ID,
    "KEYCLOAK_CLIENT_SECRET": Config.KEYCLOAK_CLIENT_SECRET,
}

for name, value in required_config.items():
    if not value:
        raise RuntimeError(f"{name} cannot be empty")