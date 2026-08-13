from flask import Blueprint, url_for, session,redirect,render_template,current_app
from flask_login import login_user,logout_user, login_required
from auth import oauth, User
from urllib.parse import urlencode



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

    session["id_token"] = token["id_token"]


    login_user(user)

    return redirect(url_for("portal.home"))


@bp_auth.route("/login")
def login():
    redirect_url = url_for("auth.callback", _external=True)

    return oauth.keycloak.authorize_redirect(
        redirect_url
    )

@bp_auth.route("/logout")
@login_required
def logout():
    # Get this BEFORE clearing the local login/session data
    id_token = session.get("id_token")

    # Exact URI configured in Keycloak
    post_logout_uri = url_for(
        "auth.log_out",
        _external=True
    )

    # End local Flask-Login session
    logout_user()

    # Remove our own locally stored identity information
    session.pop("user", None)
    session.pop("id_token", None)

    # Keycloak RP-initiated logout endpoint
    logout_endpoint = (
        f"{current_app.config['KEYCLOAK_SERVER_URL']}"
        f"/realms/{current_app.config['KEYCLOAK_REALM']}"
        f"/protocol/openid-connect/logout"
    )

    params = {
        "id_token_hint": id_token,
        "post_logout_redirect_uri": post_logout_uri,
    }

    keycloak_logout_url = (
        f"{logout_endpoint}?{urlencode(params)}"
    )

    return redirect(keycloak_logout_url)


@bp_auth.route("/logged-out")
def log_out():
    return render_template("logged-out.html")