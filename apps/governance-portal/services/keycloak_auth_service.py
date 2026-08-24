import requests 

from services.exceptions import KeycloakServiceAuthenticationError

def get_service_access_token(
    token_url,
    client_id,
    client_secret
):
    """
    Authenticate the Governance backend to Keycloak using
    the OAuth 2.0 Client Credentials grant.

    The returned access token will later be used to call
    Keycloak's Admin REST API.
    """
    try : 
    
     response = requests.post(
        token_url,
        data={
             "grant_type" : "client_credentials"                      
        },
        auth=(
            client_id,
            client_secret,
        ),
        timeout=5,
        )
     response.raise_for_status()

    except requests.RequestException as exc:
        raise KeycloakServiceAuthenticationError(
            "Unable to authenticate Governence service with Keycloak"
        ) from exc

    payload = response.json()

    access_token = payload.get("access_token")

    if not access_token :
        raise KeycloakServiceAuthenticationError(
            "Keycloak response did not contain an access token"
        )

    return access_token 
        
