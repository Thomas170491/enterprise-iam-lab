from flask import Blueprint, url_for

from auth import oauth


bp_auth = Blueprint("auth", __name__)


@bp_auth.route("/auth/callback")
def callback():
    return None


@bp_auth.route("/login")
def login():
    redirect_url = url_for("auth.callback", _external=True)

    return oauth.keycloak.authorize_redirect(
        redirect_url
    )