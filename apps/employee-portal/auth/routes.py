from flask import Blueprint, url_for, session,redirect,render_template,current_app
from flask_login import login_user,logout_user, login_required
from auth import oauth, User
from urllib.parse import urlencode
import requests
from authlib.jose import JsonWebToken


bp_auth = Blueprint("auth", __name__)


@bp_auth.route("/auth/callback")
def callback():

    #Get identity information

    token = oauth.keycloak.authorize_access_token()
    userinfo = token["userinfo"]

    # 2. Extract/validate roles from access token   

    jwks_url = (
        f"{current_app.config['KEYCLOAK_SERVER_URL']}"
        f"/realms/{current_app.config['KEYCLOAK_REALM']}"
        f"/protocol/openid-connect/certs"
        )

    
    response = requests.get(jwks_url, timeout=5)
    response.raise_for_status()
    jwks = response.json()
    
    jwt=JsonWebToken(["RS256"])

    claims = jwt.decode(
        token["access_token"],
        jwks,
        claims_options={
            "iss" : {
                "essential" : True,
                "value" : (
                       f"{current_app.config['KEYCLOAK_SERVER_URL']}"
                       f"/realms/{current_app.config['KEYCLOAK_REALM']}"
                )
            }
        }
    )

    claims.validate()

    realm_roles=(
        claims
        .get("realm_access", {})
        .get("roles", [])
    )

    client_roles = (
    claims
    .get("resource_access", {})
    .get(current_app.config["KEYCLOAK_CLIENT_ID"], {})
    .get("roles", [])
    )
    # 3. Create User object

    user = User(
        sub=userinfo["sub"],
        username=userinfo["preferred_username"],
        name=userinfo["name"],
        email=userinfo["email"],
        realm_roles = realm_roles,
        client_roles = client_roles
        
    )

    # 4. Store user + roles in session

    session["user"] = {
        "sub": user.id,
        "username": user.username,
        "name": user.name,
        "email": user.email,
        "realm_roles": user.realm_roles,
        "client_roles": user.client_roles,
    }

    # 5. login_user(user)

    login_user(user)


    # Keep identity data in the server-side session
    # so user_loader() can reconstruct the User later.


    session["id_token"] = token["id_token"]


    # 6. Redirect home

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