import pytest

from services.validation import is_keycloak_uuid


@pytest.mark.parametrize(
    "value",
    [
        "3f2b8c1e-5d4a-4e6f-9a7b-1c2d3e4f5a6b",
        "3F2B8C1E-5D4A-4E6F-9A7B-1C2D3E4F5A6B",
    ],
)
def test_is_keycloak_uuid_accepts_canonical_uuid(value):
    """
    Verify that an exact Keycloak UUID is accepted in lower or upper case.
    """
    assert is_keycloak_uuid(value) is True


@pytest.mark.parametrize(
    "value",
    [
        "./3f2b8c1e-5d4a-4e6f-9a7b-1c2d3e4f5a6b",
        "../3f2b8c1e-5d4a-4e6f-9a7b-1c2d3e4f5a6b",
        "3f2b8c1e-5d4a-4e6f-9a7b-1c2d3e4f5a6b?briefRepresentation=true",
        "3f2b8c1e-5d4a-4e6f-9a7b-1c2d3e4f5a6b/groups",
        " 3f2b8c1e-5d4a-4e6f-9a7b-1c2d3e4f5a6b ",
        "3f2b8c1e5d4a4e6f9a7b1c2d3e4f5a6b",
        "user-123",
        "",
        None,
        123,
    ],
)
def test_is_keycloak_uuid_rejects_anything_else(value):
    """
    Verify that aliases, extra path or query text, padding, other formats and non-strings are rejected.
    """
    assert is_keycloak_uuid(value) is False
