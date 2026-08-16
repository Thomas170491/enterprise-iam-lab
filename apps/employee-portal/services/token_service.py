from joserfc import jwt
from joserfc.errors import (
    BadSignatureError,
    DecodeError,
    ExpiredTokenError,
    InvalidKeyIdError,
    InvalidPayloadError,
    JoseError,
    MissingAlgorithmError,
    MissingClaimError,
    UnsupportedAlgorithmError,
)

from services.exceptions import TokenValidationError
from services.jwks_service import get_key_set


def _decode_token(
    access_token,
    key_set,
):
    """
    Verify the JWT signature and decode its claims.

    InvalidKeyIdError is allowed to propagate because
    the caller can refresh the JWKS and retry once.
    """

    try:
        return jwt.decode(
            access_token,
            key_set,
            algorithms=["RS256"],
        )

    except BadSignatureError as exc:
        raise TokenValidationError(
            "bad_signature"
        ) from exc

    except (
        DecodeError,
        InvalidPayloadError,
    ) as exc:
        raise TokenValidationError(
            "malformed_token"
        ) from exc

    except (
        MissingAlgorithmError,
        UnsupportedAlgorithmError,
    ) as exc:
        raise TokenValidationError(
            "invalid_algorithm"
        ) from exc

    except JoseError as exc:
        raise TokenValidationError(
            "token_decode_failed"
        ) from exc


def _validate_expiration(claims):
    """
    Require a valid, non-expired exp claim.
    """

    registry = jwt.JWTClaimsRegistry(
        exp={
            "essential": True,
        }
    )

    try:
        registry.validate(
            claims
        )

    except ExpiredTokenError as exc:
        raise TokenValidationError(
            "expired_token"
        ) from exc

    except MissingClaimError as exc:
        raise TokenValidationError(
            "missing_expiration"
        ) from exc

    except JoseError as exc:
        raise TokenValidationError(
            "invalid_expiration"
        ) from exc


def _validate_subject(claims):
    """
    Require the token to identify a subject.
    """

    if not claims.get("sub"):
        raise TokenValidationError(
            "missing_subject"
        )


def _validate_issuer(
    claims,
    expected_issuer,
):
    """
    Require the token issuer to match our Keycloak realm.
    """

    issuer = claims.get("iss")

    if issuer is None:
        raise TokenValidationError(
            "missing_issuer"
        )

    if issuer != expected_issuer:
        raise TokenValidationError(
            "invalid_issuer"
        )


def _validate_audience(
    claims,
    expected_audience,
):
    """
    Require the expected API audience.

    JWT aud may be either a string or a list.
    """

    audience = claims.get("aud")

    if audience is None:
        raise TokenValidationError(
            "missing_audience"
        )

    if isinstance(audience, str):
        audiences = [audience]

    elif isinstance(audience, list):
        audiences = audience

    else:
        raise TokenValidationError(
            "invalid_audience"
        )

    if expected_audience not in audiences:
        raise TokenValidationError(
            "invalid_audience"
        )


def validate_access_token(
    access_token,
    server_url,
    realm,
    audience=None,
    jwks_cache_ttl_seconds=300,
):
    """
    Verify and validate a Keycloak access token.
    """

    issuer = (
        f"{server_url}/realms/{realm}"
    )

    jwks_url = (
        f"{issuer}"
        "/protocol/openid-connect/certs"
    )

    # Get cached Keycloak signing keys.
    key_set = get_key_set(
        jwks_url,
        ttl_seconds=jwks_cache_ttl_seconds,
    )

    # ========================================================
    # SIGNATURE VERIFICATION
    # ========================================================

    try:
        token = _decode_token(
            access_token,
            key_set,
        )

    except InvalidKeyIdError:
        # The cached keys may be stale because Keycloak
        # rotated its signing key.
        key_set = get_key_set(
            jwks_url,
            ttl_seconds=jwks_cache_ttl_seconds,
            force_refresh=True,
        )

        try:
            token = _decode_token(
                access_token,
                key_set,
            )

        except InvalidKeyIdError as exc:
            raise TokenValidationError(
                "invalid_key_id"
            ) from exc

    # ========================================================
    # CLAIM VALIDATION
    # ========================================================

    claims = token.claims

    _validate_expiration(
        claims
    )

    _validate_subject(
        claims
    )

    _validate_issuer(
        claims,
        issuer,
    )

    # Browser OIDC validation does not require our API
    # audience, while Bearer API authentication does.
    if audience is not None:
        _validate_audience(
            claims,
            audience,
        )

    return claims


def extract_roles(
    claims,
    client_id,
):
    """
    Extract Keycloak realm and client roles.
    """

    realm_roles = (
        claims
        .get("realm_access", {})
        .get("roles", [])
    )

    client_roles = (
        claims
        .get("resource_access", {})
        .get(client_id, {})
        .get("roles", [])
    )

    return realm_roles, client_roles