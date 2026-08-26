from services.keycloak_admin_service import search_users

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
        attributes = user.get("attributes",{})

        identity = {
            # Keycloak's internal immutable-ish identifier.
            # We use this instead of username as our primary identity reference.
            "id": user.get("id"),

            "username": user.get("username"),
            "first_name": user.get("firstName"),
            "last_name": user.get("lastName"),
            "email": user.get("email"),
            "enabled": user.get("enabled", False),

            # NovaSecure custom identity attributes.
            "employee_id": _first_attribute(attributes, "employee_id"),

            "employment_status": _first_attribute(attributes,"employment_status",),

            "job_title": _first_attribute(attributes,"job_title"),

            "risk_level": _first_attribute(attributes,"risk_level"),
        }

        identities.append(identity)

    return identities

