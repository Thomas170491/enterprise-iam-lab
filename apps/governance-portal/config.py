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

    # ========================================================
    # FLASK-SMOREST / OPENAPI
    # =======================================================

    API_TITLE = "NovaSecure IAM Governance API"

    API_VERSION = "v1"

    OPENAPI_VERSION = "3.0.3"
    
    OPENAPI_URL_PREFIX = "/api"

    OPENAPI_JSON_PATH = "openapi.json"

#Fail immediately if required configuration is missing
if not Config.SECRET_KEY :
    raise RuntimeError("FLASK_SECRET_KEY cannot be empty")


    