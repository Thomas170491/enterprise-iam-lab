from typing import Any

import requests

from services.exceptions import KeycloakAdminAPIError
from services.keycloak_auth_service import get_service_access_token


def _parse_dict_list(
    
    payload: Any,
    error_message: str,
) -> list[dict[str, Any]]:
    """
    Validate that a decoded payload is a list of dictionaries.
    """
    if not isinstance(payload, list):
        raise KeycloakAdminAPIError(error_message)

    if any(not isinstance(item, dict) for item in payload):
        raise KeycloakAdminAPIError(error_message)

    return payload


def search_users(
    admin_api_url: str,
    token_url: str,
    client_id: str,
    client_secret: str,
    search: str | None = None,
    max_results: int = 20,
) -> list[dict[str, Any]]:
    """
    Search users in the Keycloak realm through
    the Keycloak Admin REST API.

    Authentication is performed with the
    iam-governance-service service account.
    """

    # First authenticate the gouvernance backend itself
    access_token = get_service_access_token(
        token_url=token_url, client_id=client_id, client_secret=client_secret
    )

    # Parameters sent to
    # GET : /admin/realms/{realm}/users
    params = {"max": max_results}

    # Only add search when the caller actually provided one
    if search:
        params["search"] = search

    try:
        response = requests.get(
            f"{admin_api_url}/users",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
            params=params,
            timeout=5,
        )
        response.raise_for_status()

    except requests.RequestException as exc:
        raise KeycloakAdminAPIError("User search failed") from exc

    try:
        users = response.json()

    except ValueError as exc:
        raise KeycloakAdminAPIError("Invalid JSON response") from exc

    return _parse_dict_list(users, "Unexpected user response")


def get_user(
    admin_api_url: str,
    token_url: str,
    client_id: str,
    client_secret: str,
    user_id: str,
) -> dict[str, Any]:
    """
    Get a specific user in the Keycloak realm through
    the Keycloak Admin REST API.

    Authentication is performed with the
    iam-governance-service service account.
    """

    # First authenticate the gouvernance backend itself
    access_token = get_service_access_token(
        token_url=token_url, client_id=client_id, client_secret=client_secret
    )

    try:
        response = requests.get(
            f"{admin_api_url}/users/{user_id}",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
            timeout=5,
        )
        response.raise_for_status()

    except requests.RequestException as exc:
        raise KeycloakAdminAPIError("User retrieval failed") from exc

    try:
        user = response.json()

    except ValueError as exc:
        raise KeycloakAdminAPIError("Invalid JSON response") from exc

    if not isinstance(user, dict):
        raise KeycloakAdminAPIError("Unexpected user response")

    return user


def get_user_groups(
    admin_api_url: str,
    token_url: str,
    client_id: str,
    client_secret: str,
    user_id: str,
) -> list[dict[str, Any]]:
    """
    Retrieve all group memberships for a user through the Keycloak Admin REST API.

    Authenticate once and collect pages until an empty page is returned.
    Raise an error if any page fails rather than return partial results.
    """

    all_groups = []
    first = 0
    page_size=100
    
    
    # First authenticate the gouvernance backend itself
    access_token = get_service_access_token(
        token_url=token_url, 
        client_id=client_id, 
        client_secret=client_secret
    )
    while True :
        try:
            response = requests.get(
                f"{admin_api_url}/users/{user_id}/groups",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json",
                },
                timeout=5,
                params={"first" : first , "max" : page_size}
            )
            response.raise_for_status()

        except requests.RequestException as exc:
            raise KeycloakAdminAPIError("User groups retrieval failed") from exc

        try:
            groups = response.json()
            

        except ValueError as exc:
            raise KeycloakAdminAPIError("Invalid JSON response") from exc

        groups = _parse_dict_list(groups, "Unexpected user groups response")
        
        if not groups  :
            break
        
        all_groups.extend(groups)
        first += len(groups) 
        
    
    

    return all_groups

def get_group_role_mappings(
    admin_api_url :str,
    token_url : str,
    client_id : str,
    client_secret :str,
    group_id :str,
)-> dict[str, Any]:
    """
    Retrieve the realm and client role mappings assigned to a group.

    Preserve the mapped roles so their composite relationships can be
    examined separately when resolving inherited access.
    """
    
    access_token = get_service_access_token(
        token_url=token_url, 
        client_id=client_id, 
        client_secret=client_secret
    )

    try:
        response = requests.get(
            f"{admin_api_url}/groups/{group_id}/role-mappings",
            headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json",
                    },
                    timeout=5,
                    
                )
        response.raise_for_status()
    
    except requests.RequestException as exc:
        raise KeycloakAdminAPIError("Group role mapping retrieval failed") from exc
    
    
    try:
        mapping = response.json()
        
    except ValueError as exc:
        raise KeycloakAdminAPIError("Invalid JSON response") from exc

    if not isinstance(mapping, dict):
        raise KeycloakAdminAPIError("Unexpected group role mappings response")
        

    return mapping
 
def get_group(
    admin_api_url : str,
    token_url: str,
    client_id: str,
    client_secret: str,
    group_id : str,
) -> dict[str, Any]:
    """
    Retrieve a group's details for inherited-access resolution.
    """
    
    access_token = get_service_access_token(
        token_url=token_url, 
        client_id=client_id, 
        client_secret=client_secret
    )

    try:
        response = requests.get(
            f"{admin_api_url}/groups/{group_id}",
            headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json",
                    },
                    timeout=5,
                    
                )
        response.raise_for_status()
        
    except requests.RequestException as exc :
        raise KeycloakAdminAPIError("Group retrieval failed") from exc
    
    try :
        group = response.json()
        
    except ValueError as exc : 
        raise KeycloakAdminAPIError("Invalid JSON response") from exc
    
    if not isinstance(group,dict) :
        raise KeycloakAdminAPIError("Unexpected group response")
    
    return group

def get_group_ancestors(
    admin_api_url : str,
    token_url: str,
    client_id: str,
    client_secret: str,
    group_id : str,
) -> list[dict[str, Any]]:
    """
    Retrieve a group's ancestors, nearest parent first.

    Reject cycles and propagate lookup failures.
    """
    ancestors = []
    visited = {group_id}
    
    starting_group = get_group(
        admin_api_url = admin_api_url,
        token_url = token_url,
        client_id = client_id,
        client_secret = client_secret,
        group_id = group_id,
    )
    while True :
        parent_id = starting_group.get("parentId")
        
        if  parent_id is None:
            return ancestors
        
        if not isinstance(parent_id, str) or not parent_id.strip():
            raise KeycloakAdminAPIError("Invalid parent group ID")
        
        if parent_id == "" :
            raise KeycloakAdminAPIError("Invalid parent group ID")
        
        if parent_id in visited :
            raise KeycloakAdminAPIError("Group hierarchy cycle detected")
        
        parent_group = get_group(        
            admin_api_url = admin_api_url,
            token_url = token_url,
            client_id = client_id,
            client_secret = client_secret,
            group_id = parent_id,
        )
        
        visited.add(parent_id)
        ancestors.append(parent_group)
        starting_group = parent_group
    
   
        

    
    
      
def get_effective_realm_roles(
    admin_api_url: str,
    token_url: str,
    client_id: str,
    client_secret: str,
    user_id: str,
) -> list[dict[str, Any]]:
    """
    Retrieve effective realm roles for an identity.

    The composite endpoint includes roles inherited
    through composite role relationships.
    """

    # First authenticate the gouvernance backend itself
    access_token = get_service_access_token(
        token_url=token_url, client_id=client_id, client_secret=client_secret
    )

    try:
        response = requests.get(
            f"{admin_api_url}/users/{user_id}/role-mappings/realm/composite",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
            timeout=5,
        )
        response.raise_for_status()
        
    except ValueError as exc:
        raise KeycloakAdminAPIError("Effective realm roles retrieval failed") from exc

    try:
        roles = response.json()
    except ValueError as exc:
        raise KeycloakAdminAPIError("Invalid JSON response") from exc

    return _parse_dict_list(roles, "Unexpected effective realm roles response")


def get_client_uuid(
    admin_api_url: str,
    token_url: str,
    client_id: str,
    client_secret: str,
    client_name: str,
) -> str:
    """
    Retrieve the UUID of a Keycloak client by its client ID.
    """

    access_token = get_service_access_token(
        token_url=token_url, client_id=client_id, client_secret=client_secret
    )

    try:
        response = requests.get(
            f"{admin_api_url}/clients",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
            params={"clientId": client_name},
            timeout=5,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise KeycloakAdminAPIError("Client UUID retrieval failed") from exc

    try:
        results = response.json()
    except ValueError as exc:
        raise KeycloakAdminAPIError("Invalid JSON response") from exc

    results = _parse_dict_list(results, "Unexpected client UUID response")

    if len(results) == 0:
        raise KeycloakAdminAPIError("Client not found")

    client_uuid = results[0].get("id")

    if not isinstance(client_uuid, str) or not client_uuid:
        raise KeycloakAdminAPIError("Client uuid missing")

    return client_uuid


def get_effective_client_roles(
    admin_api_url: str,
    token_url: str,
    client_id: str,
    client_secret: str,
    user_id: str,
    target_client_name: str,
) -> list[dict[str, Any]]:
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
        client_name=target_client_name,
    )

    access_token = get_service_access_token(
        token_url=token_url, client_id=client_id, client_secret=client_secret
    )

    try:
        response = requests.get(
            f"{admin_api_url}/users/{user_id}"
            f"/role-mappings/clients/{client_uuid}/composite",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
            timeout=5,
        )
        response.raise_for_status()

    except requests.RequestException as exc:
        raise KeycloakAdminAPIError("Effective client roles retrieval failed") from exc

    try:
        roles = response.json()

    except ValueError as exc:
        raise KeycloakAdminAPIError("Invalid JSON response") from exc

    return _parse_dict_list(roles, "Unexpected effective client roles response")


def get_client_role(
    admin_api_url: str,
    token_url: str,
    client_id: str,
    client_secret: str,
    client_uuid: str,
    role_name: str,
) -> dict[str, Any]:
    """
    Retrieve one client role representation from Keycloak.

    A complete RoleRepresentation is required when we later
    assign the role to a user.
    """

    access_token = get_service_access_token(
        token_url=token_url, client_id=client_id, client_secret=client_secret
    )

    try:
        response = requests.get(
            (f"{admin_api_url}/clients/{client_uuid}" f"/roles/{role_name}"),
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
            timeout=5,
        )

        response.raise_for_status()

    except requests.RequestException as exc:
        raise KeycloakAdminAPIError("Client role retrieval fail") from exc

    try:
        role = response.json()
    except ValueError as exc:
        raise KeycloakAdminAPIError("Invalid JSON response") from exc

    if not isinstance(role, dict):
        raise KeycloakAdminAPIError("Unexpected JSON response")

    if not role.get("id") or not role.get("name"):
        raise KeycloakAdminAPIError("Incomplete client response")

    return role


def assign_client_role(
    admin_api_url: str,
    token_url: str,
    client_id: str,
    client_secret: str,
    user_id: str,
    client_uuid: str,
    role: dict[str, Any],
) -> None:
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
    try:
        response = requests.post(
            (
                f"{admin_api_url}/users/{user_id}/"
                f"role-mappings/clients/{client_uuid}"
            ),
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            json=[role],
            timeout=5,
        )

        response.raise_for_status()

    except requests.RequestException as exc:
        raise KeycloakAdminAPIError("Client role assignment failed") from exc


def remove_client_role(
    admin_api_url: str,
    token_url: str,
    client_id: str,
    client_secret: str,
    user_id: str,
    client_uuid: str,
    role: dict[str, Any],
) -> None:
    """
    Remove one client role from a Keycloak user.
    Keycloak expects a list of RoleRepresentation
    objects when removing client-level role mappings.

    """

    access_token = get_service_access_token(
        token_url=token_url,
        client_id=client_id,
        client_secret=client_secret,
    )

    try:
        response = requests.delete(
            (
                f"{admin_api_url}/users/{user_id}/"
                f"role-mappings/clients/{client_uuid}"
            ),
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            json=[role],
            timeout=5,
        )

        response.raise_for_status()

    except requests.RequestException as exc:
        raise KeycloakAdminAPIError("Client role removal failed") from exc


def get_direct_client_roles(
    admin_api_url: str,
    token_url: str,
    client_id: str,
    client_secret: str,
    user_id: str,
    target_client_name: str,
) -> list[dict[str, Any]]:
    """
    Retrieve client roles directly assigned to a user.
    """

    client_uuid = get_client_uuid(
        admin_api_url=admin_api_url,
        token_url=token_url,
        client_id=client_id,
        client_secret=client_secret,
        client_name=target_client_name,
    )

    access_token = get_service_access_token(
        token_url=token_url,
        client_id=client_id,
        client_secret=client_secret,
    )

    try:
        response = requests.get(
            (
                f"{admin_api_url}/users/{user_id}/"
                f"role-mappings/clients/{client_uuid}"
            ),
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
            timeout=5,
        )

        response.raise_for_status()

    except requests.RequestException as exc:
        raise KeycloakAdminAPIError("Direct client roles retrieval failed") from exc

    try:
        roles = response.json()

    except requests.RequestException as exc:
        raise KeycloakAdminAPIError("Invalid JSON response") from exc

    return _parse_dict_list(roles, "Unexpected direct client roles response")
