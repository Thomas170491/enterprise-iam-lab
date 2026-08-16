from pathlib import Path
import os

from dotenv import load_dotenv;
from cachelib.file import FileSystemCache
from sqlalchemy import URL 



BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent.parent

# Infrastructure configuration
load_dotenv(PROJECT_ROOT / ".env")

# Employee Portal-specific configuration
load_dotenv(BASE_DIR / ".env")

class Config:
    # Flask
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY")

    #Database
    PORTAL_DB = os.getenv("PORTAL_DB")
    PORTAL_DB_USER = os.getenv("PORTAL_DB_USER")
    PORTAL_DB_PASSWORD = os.getenv("PORTAL_DB_PASSWORD")
    KEYCLOAK_API_AUDIENCE = os.getenv("KEYCLOAK_API_AUDIENCE")

    SQLALCHEMY_DATABASE_URI = URL.create(
        "postgresql+psycopg",
        username=PORTAL_DB_USER,
        password=PORTAL_DB_PASSWORD,
        host="localhost",
        port=5433,
        database=PORTAL_DB,
    )

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

    SESSION_CACHELIB = FileSystemCache(
        cache_dir=str(BASE_DIR / ".flask_session"),
        threshold=500,
    )


# Validate required configuration
required_config = {
    "FLASK_SECRET_KEY": Config.SECRET_KEY,
    "KEYCLOAK_SERVER_URL": Config.KEYCLOAK_SERVER_URL,
    "KEYCLOAK_REALM": Config.KEYCLOAK_REALM,
    "KEYCLOAK_CLIENT_ID": Config.KEYCLOAK_CLIENT_ID,
    "KEYCLOAK_CLIENT_SECRET": Config.KEYCLOAK_CLIENT_SECRET,
    "PORTAL_DB": Config.PORTAL_DB,
    "PORTAL_DB_USER": Config.PORTAL_DB_USER,
    "PORTAL_DB_PASSWORD": Config.PORTAL_DB_PASSWORD,
    "KEYCLOAK_API_AUDIENCE": Config.KEYCLOAK_API_AUDIENCE,
}



for name, value in required_config.items():
    if not value:
        raise RuntimeError(f"{name} cannot be empty")