from flask import (
    Blueprint,
    redirect,
    session,
    url_for,
)
from flask_login import login_user

from auth.user import User
from extensions import oauth


bp_auth = Blueprint(
    "auth",
    __name__,
)


@bp_auth.get("/login")
def login():
    """
    Start the OIDC Authorization Code Flow.
    """

    redirect_uri = url_for(
        "auth.callback",
        _external=True,
    )

    return oauth.keycloak.authorize_redirect(
        redirect_uri
    )


@bp_auth.get("/auth/callback")
def callback():
    """
    Handle the authorization response from Keycloak.
    """

    # Exchange the authorization code for tokens.
    token = oauth.keycloak.authorize_access_token()
   

    # Authlib normally extracts OIDC userinfo from
    # the validated ID token.
    userinfo = token.get("userinfo")

    if not userinfo:
        userinfo = oauth.keycloak.userinfo(
            token=token
        )

    

    user = User(
        sub=userinfo['sub'],
        name=userinfo["name"],
        username=userinfo.get(
            "preferred_username"
        ),
        email=userinfo.get("email"),

        # Role extraction comes in the next step.
        client_roles=[],
        realm_roles=[],
    )

    session["user"] = {
        "sub": user.sub,
        "name": user.name,
        "username": user.username,
        "email": user.email,
        "client_roles": [],
        "realm_roles": [],
    }

    login_user(user)

    return redirect(
        url_for("governance.dashboard")
    )