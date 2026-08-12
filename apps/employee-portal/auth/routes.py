from flask import Blueprint, url_for, session,redirect

from auth import oauth


bp_auth = Blueprint("auth", __name__)


@bp_auth.route("/auth/callback")
def callback():
    token = oauth.keycloak.authorize_access_token()
    userinfo = token['userinfo']
    session["user"] = {
    "sub": userinfo["sub"],
    "username": userinfo["preferred_username"],
    "name": userinfo["name"],
    "email": userinfo["email"],
}
    return redirect(url_for("portal.home"))


@bp_auth.route("/login")
def login():
    redirect_url = url_for("auth.callback", _external=True)

    return oauth.keycloak.authorize_redirect(
        redirect_url
    )