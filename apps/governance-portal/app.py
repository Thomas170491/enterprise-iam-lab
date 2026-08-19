from flask import Flask

from api import blp_health
from config import Config
from extensions import (
    api,
    login_manager,
    oauth,
    session_manager,
)
from governance import bp_governance
import auth 


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # REST API / OpenAPI
    api.init_app(app)

    # OIDC
    oauth.init_app(app)

    # Flask-Login
    login_manager.init_app(app)

    # Server-side session storage
    session_manager.init_app(app)

    # Application routes
    app.register_blueprint(bp_governance)

    # REST API blueprints
    api.register_blueprint(blp_health)

    return app


app = create_app()