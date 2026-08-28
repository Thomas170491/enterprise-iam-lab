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
                "Authorization" : f"Bearer {access_token}",
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


def get_client_uuid(
        admin_api_url,
        token_url,
        client_id,
        client_secret,
        client_name
) :
    """
    Retrieve the UUID of a Keycloak client by its name.
    """

    access_token = get_service_access_token(
        token_url = token_url,
        client_id = client_id,
        client_secret = client_secret
    )

    try : 
        response = requests.get(
            f"{admin_api_url}/clients",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json"
            },
            params={
                "clientId": client_name
            },
            timeout=5
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise KeycloakAdminAPIError("Client UUID retrieval failed") from exc

    try: 
        results = response.json()
    except ValueError as exc:
        raise KeycloakAdminAPIError("Invalid JSON response") from exc

    if not isinstance(results,list) :
        raise KeycloakAdminAPIError("Unexpected client UUID response")

    if len(results) == 0:
        raise KeycloakAdminAPIError("Client not found")

    client_uuid = results[0].get("id")

    if not client_uuid:
        raise KeycloakAdminAPIError("Client uuid missing")

    return client_uuid 

def get_effective_client_roles(
        admin_api_url,
        token_url,
        client_id,
        client_secret,
        user_id,
        target_client_name
):
    """
    Retrieve effective client roles for an identity.

    The target client's internal Keycloak UUID is resolved
    before querying the composite client role mappings.
    """

    client_uuid = get_client_uuid(
        admin_api_url=admin_api_url,
        token_url=token_url,
        client_id=client_id,
        client_secret=client_secret,
        client_name=target_client_name
    )

    access_token = get_service_access_token(
        token_url=token_url,
        client_id=client_id,
        client_secret=client_secret
    )

    try:
        response = requests.get(
            f"{admin_api_url}/users/{user_id}"
            f"/role-mappings/clients/{client_uuid}/composite",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json"
            },
            timeout=5
        )
        response.raise_for_status()

    except requests.RequestException as exc:
        raise KeycloakAdminAPIError(
            "Effective client roles retrieval failed"
        ) from exc

    try:
        roles = response.json()

    except ValueError as exc:
        raise KeycloakAdminAPIError(
            "Invalid JSON response"
        ) from exc

    if not isinstance(roles, list):
        raise KeycloakAdminAPIError(
            "Unexpected effective client roles response"
        )

    return roles

def get_client_role(
        admin_api_url,
        token_url,
        client_id,
        client_secret,
        client_uuid,
        role_name,
):
    """
    Retrieve one client role representation from Keycloak.

    A complete RoleRepresentation is required when we later
    assign the role to a user.
    """

    access_token = get_service_access_token(
        token_url=token_url,
        client_id=client_id,
        client_secret=client_secret
    )

    try : 
        response = requests.get(
            (
            f"{admin_api_url}/clients/{client_uuid}"
            f"/roles/{role_name}"
        ),
        headers = {
            "Authorization" : f"Bearer {access_token}",
            "Accept" : "application/json"
        },
        timeout= 5
        )
    except requests.RequestException as exc:
        raise KeycloakAdminAPIError("Client role retrieval fail") from exc 

    try : 
        role = response.json()
    except ValueError as exc :
        raise KeycloakAdminAPIError("Invalid JSON respon") from exc 

    if not isinstance(role, dict) : 
        raise KeycloakAdminAPIError("Unexpected JSON response")

    if not role.get("id") or not role.get("name") :
        raise KeycloakAdminAPIError("Incomplete clien response")

    return role

def assign_client_role(
        admin_api_url,
        token_url,
        client_id,
        client_secret,
        user_id,
        client_uuid,
        role,
):
    """
    Assign one client role to a Keycloak user.

    Keycloak expects a list of RoleRepresentation
    objects when assigning client-level role mappings.
    """

    access_token = get_service_access_token(
        token_url=token_url,
        client_id=client_id,
        client_secret=client_secret,
    ) 
    try :
        response = requests.post(
            (
                f"{admin_api_url}/users/{user_id}/"
                f"role-mappings/clients/{client_uuid}"
            ),

            headers= {
                "Authorization" : f"Bearer {access_token}",
                "Accept" : "application/json",
                "Content-Type" :"application/json"
            },

            json=[role],

            timeout=5,

        )

        response.raise_for_status()

    except requests.RequestException as exc :
        raise KeycloakAdminAPIError("Client role assignment failed") from exc

     


 
