from services.keycloak_admin_service import (
    search_users,
    get_user,
    get_user_groups,
    get_effective_realm_roles,
    get_effective_client_roles,
    get_direct_client_roles
)

def _first_attribute(attributes ,name):
    """
    Keycloak custom attributes are normally returned
    as lists of strings.

    Example:
        {
            "employee_id": ["e1004"],
            "job_title": ["IAM Operator"]
        }

    This helper returns the first value, or None
    when the attribute does not exist.
    """
    values = attributes.get(name, [])

    if not values :
        return None

    return values[0]


def _normalize_identity(user):
    attributes = user.get("attributes", {})

    return {
        "id": user.get("id"),
        "username": user.get("username"),
        "first_name": user.get("firstName"),
        "last_name": user.get("lastName"),
        "email": user.get("email"),
        "enabled": user.get("enabled", False),
        "employee_id": _first_attribute(
            attributes,
            "employee_id"
        ),
        "employment_status": _first_attribute(
            attributes,
            "employment_status"
        ),
        "job_title": _first_attribute(
            attributes,
            "job_title"
        ),
        "risk_level": _first_attribute(
            attributes,
            "risk_level"
        ),
    }


def search_identities( 
        admin_api_url,
        token_url,
        client_id,
        client_secret,
        search = None,
        max_results = 20
) : 
    """
    Search identities in Keycloak and convert the raw
    Keycloak UserRepresentation objects into the simpler
    identity format used by the Governance Portal.
    """

    users= search_users(
        admin_api_url=admin_api_url,
        token_url=token_url,
        client_id=client_id,
        client_secret=client_secret,
        search=search,
        max_results=max_results
    )

    identities = []

    for user in users : 
        identity = _normalize_identity(user)
        identities.append(identity)

    return identities

        

def get_identity_access(
        admin_api_url,
        token_url,
        client_id,
        client_secret,
        user_id,
        target_client_name
):
    """
    Retrieve and aggregate the effective access of
    a specific identity.

    Combines the user's identity information, groups,
    effective realm roles, and effective client roles.
    """

    user = get_user(
        admin_api_url=admin_api_url,
        token_url=token_url,
        client_id=client_id,
        client_secret=client_secret,
        user_id=user_id,
    )

    groups = get_user_groups(
        admin_api_url=admin_api_url,
        token_url=token_url,
        client_id=client_id,
        client_secret=client_secret,
        user_id=user_id,
    )

    realm_roles = get_effective_realm_roles(
        admin_api_url=admin_api_url,
        token_url=token_url,
        client_id=client_id,
        client_secret=client_secret,
        user_id=user_id,
    )

    client_roles = get_effective_client_roles(
        admin_api_url=admin_api_url,
        token_url=token_url,
        client_id=client_id,
        client_secret=client_secret,
        user_id=user_id,
        target_client_name=target_client_name,
    )

    direct_client_roles = get_direct_client_roles(
        admin_api_url=admin_api_url,
        token_url=token_url,
        client_id=client_id,
        client_secret=client_secret,
        user_id=user_id,
        target_client_name=target_client_name,
    )

    identity = _normalize_identity(user)

    return {
        "identity": identity,
        "groups": groups,
        "realm_roles": realm_roles,
        "client_roles": client_roles,
        "direct_client_roles" : direct_client_roles
    }

