from functools import wraps

import requests
from flask import current_app, g, request
from flask_login import current_user
from services.exceptions import TokenValidationError
from api.errors import api_error
from auth import User
from services.token_service import (
    validate_access_token,
    extract_roles,
)


def api_login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):

        # 1. Existing browser session
        if current_user.is_authenticated:
            g.api_user = current_user
            return view(*args, **kwargs)

        # 2. No browser session: look for Bearer token
        authorization = request.headers.get("Authorization")

        if authorization is None:
            return api_error(
                "authentication_required",
                "Authentication is required.",
                401,
            )

        parts = authorization.split(None, 1)

        if (
            len(parts) != 2
            or parts[0].lower() != "bearer"
            or not parts[1].strip()
        ):
            return api_error(
                "invalid_authorization_header",
                "A valid Bearer token is required.",
                401,
            )

        access_token = parts[1].strip()

        try:
            claims = validate_access_token(
                access_token,
                current_app.config["KEYCLOAK_SERVER_URL"],
                current_app.config["KEYCLOAK_REALM"],
                audience=current_app.config["KEYCLOAK_API_AUDIENCE"],
            )

        except TokenValidationError as exc:
            current_app.logger.warning(
            "Bearer token validation failed: %s",
            exc.reason,   
            )
            # Externally, return a generic error so we do not reveal
            # exactly why token validation failed.
            return api_error(
                "invalid_access_token",
                "The access token is invalid or expired.",
                401,
    )
        except requests.RequestException:
            return api_error(
                "identity_provider_unavailable",
                "The identity provider is unavailable.",
                503,
            )

        realm_roles, client_roles = extract_roles(
            claims,
            current_app.config["KEYCLOAK_CLIENT_ID"],
        )

        g.api_user = User(
            sub=claims["sub"],
            username=claims.get(
                "preferred_username",
                claims["sub"],
            ),
            name=claims.get(
                "name",
                claims.get("preferred_username", claims["sub"]),
            ),
            email=claims.get("email"),
            realm_roles=realm_roles,
            client_roles=client_roles,
        )

        return view(*args, **kwargs)

    return wrapped