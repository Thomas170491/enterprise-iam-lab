class TokenValidationError(Exception):

    """
    Internal application exception for failed JWT validation.

    'reason' is safe for logging/SIEM classification.
    The raw JWT must never be stored in this exception.
    """
    def __init__(self,reason) :
        self.reason = reason

        super().__init__(
            f"Access token validation failed: {reason}"
        )

class KeycloakServiceAuthenticationError(Exception):
        """
    Raised when the Governance backend cannot authenticate
    its service account with Keycloak.
    """
        pass

class KeycloakAdminAPIError(Exception):
    """
    Raised when communication with the
    Keycloak Admin REST API fails.
    """

    def __init__(self, reason):
        self.reason = reason
        super().__init__(
            f"Keycloak Admin API request failed: {reason}"
        )