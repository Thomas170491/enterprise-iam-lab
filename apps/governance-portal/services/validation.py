import re 

_KEYCLOAK_UUID = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.IGNORECASE,
)

def is_keycloak_uuid(value: str) -> bool:
    
    """
    Check if the given value is a valid Keycloak UUID.

    Args:
        value (str): The value to check.
    """
    
    return isinstance(value,str) and _KEYCLOAK_UUID.fullmatch(value)is not None