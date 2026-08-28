from flask_smorest import Api
from flask_login import LoginManager
from authlib.integrations.flask_client import OAuth
from flask_session import Session 
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect



# Flask-Smorest API extension.
#
# We create it here without binding it immediately
# to a Flask application. app.py will initialize it
# inside the application factory.
api = Api()

# OIDC client used to communicate with Keycloak
oauth = OAuth()

# Browser authentication session management
login_manager = LoginManager()

# Server-side Flask sessions
session_manager = Session()

#Database migrations
db =SQLAlchemy()
migrate = Migrate()

#CSRF
csrf=CSRFProtect()

