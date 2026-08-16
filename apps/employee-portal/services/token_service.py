import requests

from joserfc import jwt 
from joserfc.jwk import KeySet

def validate_access_token(access_token, server_url,realm ):
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

    claims_registery = jwt.JWTClaimsRegistry(
        iss={
            "essential": True,
            "value": issuer,
        },
        exp={
            "essential": True,
        },
        sub={
            "essential": True,
        },
    )
    claims_registery.validate(
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