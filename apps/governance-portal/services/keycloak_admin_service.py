import requests

from services.exceptions import KeycloakAdminAPIError
from services.keycloak_auth_service import get_service_access_token

def search_users(
        admin_api_url,
        token_url,
        client_id,
        client_secret,
        search = None,
        max_results =20
):
    """
    Search users in the Keycloak realm through
    the Keycloak Admin REST API.

    Authentication is performed with the
    iam-governance-service service account.
    """

    #First authenticate the gouvernance backend itself
    access_token = get_service_access_token(
        token_url=token_url,
        client_id=client_id,
        client_secret=client_secret
    )

    #Parameters sent to
    # GET : /admin/realms/{realm}/users
    params ={
        "max":max_results
    }

    #Only add search when the caller actually provided one
    if search:
        params["search"] = search

    try :
        response = requests.get(
            f"{admin_api_url}/users",
            headers={
                "Authorization" : f"Bearer {access_token}",
                "Accept" : "application/json"

            },
            params=params,
            timeout=5
        )
        response.raise_for_status()

    except requests.RequestException as exc:
        raise KeycloakAdminAPIError("User search failed") from exc 

    try :
        users= response.json()

    except ValueError as exc:
        raise KeycloakAdminAPIError("Invalid JSON response") from exc 

    if not isinstance(users,list) :
        raise KeycloakAdminAPIError("Unexpected user response")

    return users