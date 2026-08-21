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

def _decode_token(access_token, key_set):
    """
    Verify the JWT signature and decode its claims.

    InvalidKeyIdError is deliberately allowed to
    propagate so the caller can refresh the JWKS
    and retry once.
    """
    try :
        return jwt.decode(access_token, key_set, algorithms=["RS256"])
    except InvalidKeyIdError : 
        raise 
    
    except BadSignatureError as exc:
        raise TokenValidationError("bad signature") from exc 
    
    except (DecodeError, InvalidPayloadError) as exc:
        raise TokenValidationError("malformed token") from exc

    except (MissingAlgorithmError, UnsupportedAlgorithmError) as exc:
        raise TokenValidationError ("invalid algorithm") from exc

    except JoseError as exc:
        raise TokenValidationError("token decode failed") from exc

def _validate_expiration(claims):
    """
    Require a valid and non-expired exp claim.
    """
    registey = jwt.JWTClaimsRegistry(
       exp ={
            "essential" : True,
        }
    ) 
    try: 
        registey.validate(claims)

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
    Require the token to identify a subject
    """    

    if not claims.get("sub") :
        raise TokenValidationError(
            "missing subject"
        )  

def _validate_issuer(claims, expected_issuer):
    """
    Require the issuer match our keycloak realm
    """

    issuer = claims.get("iss")

    if issuer is None :
        raise TokenValidationError("missing issuer")

    if issuer != expected_issuer :
        raise TokenValidationError("invalid issuer")

def _validate_audience(claims, expected_audience) :

    audience = claims.get("aud")

    if audience is None :
        raise TokenValidationError("missing audience")

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
        realm, audience = None, 
        jwks_cache_ttl_seconds =300
        ):

    """
    Verify and validate a Keycloak access token.
    """

    issuer = f"{server_url}/realms/{realm}"

    jwks_url = f"{issuer}/protocol/openid-connect/certs"

    key_set = get_key_set(jwks_url, jwks_cache_ttl_seconds)

    try : 
        token= _decode_token(access_token, key_set)

    except InvalidKeyIdError :
        key_set = get_key_set(jwks_url, jwks_cache_ttl_seconds, force_refresh=True)

        try :
            _decode_token(access_token, key_set)

        except InvalidKeyIdError as exc :
            raise TokenValidationError("Invalid Key Id") from exc

    claims = token.claims

    _validate_expiration(claims)
    _validate_subject(claims)
    _validate_issuer(claims,issuer)

    if audience is not None :
     _validate_audience(claims,audience)

    return claims 

def extract_roles(claims,client_id) :

    realm_roles = (
        claims
        .get("realm_access",{})
        .get("roles", [])
    )
    client_roles = (
        claims
        .get("resource_access", {})
        .get(client_id,{})
        .get("roles", [])
    )

    return realm_roles, client_roles




        



        


        