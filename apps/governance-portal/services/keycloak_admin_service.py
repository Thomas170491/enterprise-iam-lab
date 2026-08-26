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

def get_user(
        admin_api_url,
        token_url,
        client_id,
        client_secret,
        user_id,
):
    """
    Get a specific user in the Keycloak realm through
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

    try :
        response = requests.get(
            f"{admin_api_url}/users/{user_id}",
            headers={
                "Authorization" : f"Bearer {access_token}",
                "Accept" : "application/json"

            },
            timeout=5
        )
        response.raise_for_status()

    except requests.RequestException as exc:
        raise KeycloakAdminAPIError("User retrieval failed") from exc 

    try :
        user= response.json()

    except ValueError as exc:
        raise KeycloakAdminAPIError("Invalid JSON response") from exc 

    if not isinstance(user,dict) :
        raise KeycloakAdminAPIError("Unexpected user response")

    return user  

def get_user_groups(
        admin_api_url,
        token_url,
        client_id,
        client_secret,
        user_id,
):
    """
    Get the groups of a specific user in the Keycloak realm through
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

    try :
        response = requests.get(
            f"{admin_api_url}/users/{user_id}/groups",
            headers={
                "Authorization" : f"Bearer {access_token}",
                "Accept" : "application/json"

            },
            timeout=5
        )
        response.raise_for_status()
 
    except requests.RequestException as exc:
        raise KeycloakAdminAPIError("User groups retrieval failed") from exc 

    try :
        groups= response.json()

    except ValueError as exc:
        raise KeycloakAdminAPIError("Invalid JSON response") from exc 

    if not isinstance(groups,list) :
        raise KeycloakAdminAPIError("Unexpected user groups response")

    return groups



def get_effective_realm_roles(
        admin_api_url,
        token_url,
        client_id,
        client_secret,
        user_id,
        ) : 
    """
    Retrieve effective realm roles for an identity.

    The composite endpoint includes roles inherited
    through composite role relationships.
    """

    #First authenticate the gouvernance backend itself
    access_token=get_service_access_token(
    token_url=token_url,
    client_id=client_id,
    client_secret=client_secret
    )

    try : 
        response=requests.get(
            f"{admin_api_url}/users/{user_id}/role-mappings/realm/composite",
            headers={
                "Authorization" : "Bearer {access_token}",
                "Accept" : "application/json"
            },
            timeout=5
        )
        response.raise_for_status()
    except requests.RequestException as exc: 
        raise KeycloakAdminAPIError("Effective realm roles retrieval failed") from exc 

    try :
        roles = response.json()
    except ValueError as exc:
        raise KeycloakAdminAPIError("Invalid JSON response") from exc

    if not isinstance(roles,list) :
        raise KeycloakAdminAPIError("Unexpected effective realm roles response")

    return roles

