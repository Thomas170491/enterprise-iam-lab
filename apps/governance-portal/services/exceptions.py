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
