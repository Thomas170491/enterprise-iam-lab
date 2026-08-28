from services.exceptions import RoleAdministrationPolicyError 
from services.keycloak_admin_service import (
    get_client_uuid,
    get_client_role,
    assign_client_role,
    remove_client_role,
)

# The Governance Portal is currently allowed to administer
# application access for the Employee Portal only.
#
# This prevents a future ROLE_MANAGER from using the same
# functionality to modify Governance Portal administrative roles.
MANAGED_CLIENTS = {
    "employee-portal",
}

def _ensure_managed_clients(target_client_name):
    """
    Reject role changes for clients that are outside the
    Governance Portal's administration scope.
    """
    if target_client_name not in MANAGED_CLIENTS:
        raise RoleAdministrationPolicyError("unmanaged client")


def assign_identity_client_role( 
        admin_api_url,
        token_url,
        client_id,
        client_secret,
        user_id,
        target_client_name,
        role_name
        ):
    """
    Assign a managed client role to an identity.

    This service coordinates the lower-level Keycloak
    Admin API operations required for role assignment.
    """ 
    _ensure_managed_clients(target_client_name)

    # Keycloak's role-mapping API requires the client's
    # internal UUID rather than its human-readable clientId.
    client_uuid = get_client_uuid(
        admin_api_url= admin_api_url,
        token_url=token_url,
        client_id= client_id,
        client_secret=client_secret,
        client_name = target_client_name,
    )

    # Retrieve the complete Keycloak RoleRepresentation.
    role = get_client_role(
            admin_api_url=admin_api_url,
            token_url = token_url,
            client_id = client_id,
            client_secret = client_secret,
            client_uuid=client_uuid,
            role_name=role_name

    )

    # Perform the actual Keycloak mutation.
    assign_client_role(
        admin_api_url=admin_api_url,
        token_url=token_url,
        client_id=client_id,
        client_secret=client_secret,
        user_id=user_id,
        client_uuid=client_uuid,
        role=role,
    )

    # Return a normalized result that the audit layer
    # will be able to use later.
    return {
        "user_id": user_id,
        "client_name": target_client_name,
        "role_id": role["id"],
        "role_name": role["name"],
    }
def remove_identity_client_role(
        admin_api_url,
        token_url,
        client_id,
        client_secret,
        user_id,
        target_client_name,
        role_name
        ):
    """
    Removes a managed client role to an identity.

    This service coordinates the lower-level Keycloak
    Admin API operations required for role assignment.
    """ 
    _ensure_managed_clients(target_client_name)

    # Keycloak's role-mapping API requires the client's
    # internal UUID rather than its human-readable clientId.
    client_uuid = get_client_uuid(
        admin_api_url= admin_api_url,
        token_url=token_url,
        client_id= client_id,
        client_secret=client_secret,
        client_name = target_client_name,
    )

    # Retrieve the complete Keycloak RoleRepresentation.
    role = get_client_role(
            admin_api_url=admin_api_url,
            token_url = token_url,
            client_id = client_id,
            client_secret = client_secret,
            client_uuid=client_uuid,
            role_name=role_name

    )

    # Perform the actual Keycloak mutation.
    remove_client_role(
        admin_api_url=admin_api_url,
        token_url=token_url,
        client_id=client_id,
        client_secret=client_secret,
        user_id=user_id,
        client_uuid=client_uuid,
        role=role,
    )

    # Return a normalized result that the audit layer
    # will be able to use later.
    return {
        "user_id": user_id,
        "client_name": target_client_name,
        "role_id": role["id"],
        "role_name": role["name"],
    } 


