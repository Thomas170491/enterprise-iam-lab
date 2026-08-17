from flask import Flask

from api import blp_health
from config import Config
from extensions import api
from governance import bp_governance


def create_app():
    """
    Create and configure the IAM Governance Portal.
    """

    app = Flask(__name__)

    # --------------------------------------------------------
    # Configuration
    # --------------------------------------------------------

    app.config.from_object(
        Config
    )

    # --------------------------------------------------------
    # Extensions
    # --------------------------------------------------------

    # Initialize Flask-Smorest.
    api.init_app(app)

    # --------------------------------------------------------
    # HTML frontend
    # --------------------------------------------------------

    app.register_blueprint(
        bp_governance
    )

    # --------------------------------------------------------
    # REST API
    # --------------------------------------------------------

    # Flask-Smorest blueprints are registered through the
    # Api extension rather than app.register_blueprint().
    api.register_blueprint(
        blp_health
    )

    return app


app = create_app()