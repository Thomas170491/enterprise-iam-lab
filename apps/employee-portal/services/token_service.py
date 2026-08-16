import requests

from joserfc import jwt 
from joserfc.jwk import KeySet

def validate_access_token(access_token, server_url,realm, audience=None ):
    issuer= f"{server_url}/realms/{realm}"

    jwks_url = (
        f"{issuer}"
        f"/protocol/openid-connect/certs"
    )

    reponse = requests.get(
        jwks_url,
        timeout=5
    )
    reponse.raise_for_status()

    keyset = KeySet.import_key_set(
        reponse.json()
    )

    token =jwt.decode(
        access_token,
        keyset,
        algorithms=["RS256"]
    )

    claims_options = {
        "iss": {
            "essential": True,
            "value": issuer,
        },
        "exp": {
            "essential": True,
        },
        "sub": {
            "essential": True,
        },
    }

    if audience is not None:
        claims_options["aud"] = {
            "essential": True,
            "value": audience,
    }

    claims_registry = jwt.JWTClaimsRegistry(
        **claims_options
    )
    claims_registry.validate(
            token.claims

    )

    return token.claims

def extract_roles(claims, client_id):
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