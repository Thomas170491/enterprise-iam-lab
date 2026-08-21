from services.exceptions import TokenValidationError




def test_token_validation_error_preserves_reason():
    """
    Security-sensitive token failures should retain
    a safe internal classification.
    """

    error = TokenValidationError(
        "expired_token"
    )

    assert error.reason ==  "expired_token"
    assert str(error) == "Access token validation failed: expired_token"