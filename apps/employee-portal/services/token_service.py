import threading
import time

import requests

from joserfc import jwt
from joserfc.errors import InvalidKeyIdError
from joserfc.jwk import KeySet


# ============================================================
# JWKS CACHE
# ============================================================

# Stores Keycloak's public signing keys in memory.
#
# Example structure:
#
# {
#     "http://localhost:8080/.../certs": {
#         "key_set": <KeySet object>,
#         "fetched_at": 123456.78
#     }
# }
#
# We cache the keys because we do NOT want to contact Keycloak
# every time somebody sends a Bearer token to our API.
_JWKS_CACHE = {}


# Flask can process several requests at the same time.
#
# Multiple threads could therefore try to read/update
# _JWKS_CACHE simultaneously.
#
# The lock ensures that only one thread manipulates the cache
# at a time.
_JWKS_CACHE_LOCK = threading.Lock()


# ============================================================
# FETCH KEYCLOAK PUBLIC KEYS
# ============================================================

def _fetch_key_set(jwks_url):
    """
    Download Keycloak's current public signing keys.

    These public keys are used to verify JWT signatures.
    """

    # Contact Keycloak's JWKS endpoint.
    response = requests.get(
        jwks_url,
        timeout=5,
    )

    # Raise an exception if Keycloak returned something such
    # as 404, 500, 503, etc.
    response.raise_for_status()

    # Keycloak returns a JWKS JSON document.
    #
    # KeySet.import_key_set() converts that JSON structure
    # into a joserfc KeySet that jwt.decode() can use.
    return KeySet.import_key_set(
        response.json()
    )


# ============================================================
# GET KEYS FROM CACHE OR KEYCLOAK
# ============================================================

def _get_key_set(
    jwks_url,
    ttl_seconds=300,
    force_refresh=False,
):
    """
    Return the Keycloak signing keys.

    Use the cached keys when they are still fresh.
    Otherwise download a fresh copy from Keycloak.

    force_refresh=True ignores the cache completely.
    """

    # monotonic() is useful for measuring elapsed time.
    #
    # Unlike the normal system clock, it won't suddenly jump
    # backward/forward if the computer's clock changes.
    now = time.monotonic()

    # Only one thread at a time may inspect/update this cache.
    with _JWKS_CACHE_LOCK:

        # Try to find previously downloaded keys for this
        # particular JWKS URL.
        cached = _JWKS_CACHE.get(jwks_url)

        # Reuse the cached keys only when:
        #
        # 1. Something is actually cached.
        # 2. Nobody explicitly asked us to refresh it.
        # 3. The cached copy is younger than the TTL.
        if (
            cached is not None
            and not force_refresh
            and now - cached["fetched_at"] < ttl_seconds
        ):
            return cached["key_set"]

        # No usable cached copy exists, so retrieve the
        # current keys from Keycloak.
        key_set = _fetch_key_set(jwks_url)

        # Store the freshly downloaded keys along with the
        # time at which they were retrieved.
        _JWKS_CACHE[jwks_url] = {
            "key_set": key_set,
            "fetched_at": time.monotonic(),
        }

        return key_set


# ============================================================
# VALIDATE ACCESS TOKEN
# ============================================================

def validate_access_token(
    access_token,
    server_url,
    realm,
    audience=None,
    jwks_cache_ttl_seconds=300,
):
    """
    Verify and validate a Keycloak access token.

    Checks include:
    - JWT signature
    - signing algorithm
    - issuer
    - expiration
    - subject
    - audience, when requested
    """

    # Expected issuer of tokens from our Keycloak realm.
    #
    # Example:
    # http://localhost:8080/realms/novasecure
    issuer = f"{server_url}/realms/{realm}"

    # Keycloak endpoint exposing the public keys used to
    # verify signed JWTs.
    jwks_url = (
        f"{issuer}"
        f"/protocol/openid-connect/certs"
    )

    # Get Keycloak's public keys.
    #
    # Usually this comes from our cache rather than from
    # another HTTP request.
    key_set = _get_key_set(
        jwks_url,
        ttl_seconds=jwks_cache_ttl_seconds,
    )

    try:
        # Cryptographically verify and decode the JWT.
        #
        # algorithms=["RS256"] prevents accepting some
        # unexpected JWT signing algorithm.
        token = jwt.decode(
            access_token,
            key_set,
            algorithms=["RS256"],
        )

    except InvalidKeyIdError:
        # ----------------------------------------------------
        # KEY ROTATION HANDLING
        # ----------------------------------------------------
        #
        # JWT headers contain a "kid" (Key ID).
        #
        # Example:
        #
        # {
        #     "alg": "RS256",
        #     "kid": "abc123"
        # }
        #
        # If Keycloak rotates its signing key, our cached
        # KeySet might not yet contain the new kid.
        #
        # Instead of immediately rejecting the token:
        #
        #     1. Ignore the cache.
        #     2. Download Keycloak's newest keys.
        #     3. Try verification once more.

        key_set = _get_key_set(
            jwks_url,
            ttl_seconds=jwks_cache_ttl_seconds,
            force_refresh=True,
        )

        token = jwt.decode(
            access_token,
            key_set,
            algorithms=["RS256"],
        )

    # ========================================================
    # CLAIM VALIDATION
    # ========================================================

    claims_options = {
        # Token must have been issued by our expected
        # Keycloak realm.
        "iss": {
            "essential": True,
            "value": issuer,
        },

        # Token must contain an expiration timestamp.
        "exp": {
            "essential": True,
        },

        # Token must identify a subject/user.
        "sub": {
            "essential": True,
        },
    }

    # Audience validation is optional because this same
    # function is also reused by the browser OIDC login flow.
    #
    # For Bearer API authentication we pass:
    #
    # audience="employee-portal-api"
    #
    # which requires the token to actually be intended for
    # our API.
    if audience is not None:
        claims_options["aud"] = {
            "essential": True,
            "value": audience,
        }

    # Create the rules that joserfc will use to validate
    # the claims.
    claims_registry = jwt.JWTClaimsRegistry(
        **claims_options
    )

    # Validate the decoded claims against those rules.
    #
    # Invalid issuer, expired token, missing subject,
    # wrong audience, etc. will raise an exception.
    claims_registry.validate(
        token.claims
    )

    # Return the verified + validated claims to the caller.
    return token.claims


# ============================================================
# ROLE EXTRACTION
# ============================================================

def extract_roles(claims, client_id):
    """
    Extract Keycloak realm roles and application client roles
    from an already validated token.
    """

    # Realm-level roles look like:
    #
    # "realm_access": {
    #     "roles": [
    #         "employee",
    #         "manager"
    #     ]
    # }
    realm_roles = (
        claims
        .get("realm_access", {})
        .get("roles", [])
    )

    # Client-specific roles look like:
    #
    # "resource_access": {
    #     "employee-portal": {
    #         "roles": [
    #             "portal-user",
    #             "finance-data-viewer"
    #         ]
    #     }
    # }
    client_roles = (
        claims
        .get("resource_access", {})
        .get(client_id, {})
        .get("roles", [])
    )

    return realm_roles, client_roles