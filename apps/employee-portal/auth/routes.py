from flask import Blueprint, url_for, session,redirect
from flask_login import login_user
from auth import oauth, User



bp_auth = Blueprint("auth", __name__)


@bp_auth.route("/auth/callback")
def callback():
    token = oauth.keycloak.authorize_access_token()
    userinfo = token["userinfo"]

    user = User(
        sub=userinfo["sub"],
        username=userinfo["preferred_username"],
        name=userinfo["name"],
        email=userinfo["email"],
    )

    # Keep identity data in the server-side session
    # so user_loader() can reconstruct the User later.
    session["user"] = {
        "sub": user.id,
        "username": user.username,
        "name": user.name,
        "email": user.email,
    }

    login_user(user)

    return redirect(url_for("portal.home"))


@bp_auth.route("/login")
def login():
    redirect_url = url_for("auth.callback", _external=True)

    return oauth.keycloak.authorize_redirect(
        redirect_url
    )