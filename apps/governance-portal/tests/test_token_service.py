import pytest

from services.exceptions import TokenValidationError
from services.token_service import (
    _validate_audience,
    _validate_issuer,
    _validate_subject,
    extract_roles,
)


def test_extract_roles():
    claims = {
        "realm_access": {
            "roles": [
                "employee",
                "privileged-user",
            ]
        },
        "resource_access": {
            "iam-admin-portal": {
                "roles": [
                    "identity-viewer",
                    "identity-manager",
                    "role-manager",
                ]
            }
        },
    }

    realm_roles, client_roles = extract_roles(
        claims,
        "iam-admin-portal",
    )

    assert realm_roles == [
        "employee",
        "privileged-user",
    ]

    assert client_roles == [
        "identity-viewer",
        "identity-manager",
        "role-manager",
    ]


def test_extract_roles_handles_missing_roles():
    realm_roles, client_roles = extract_roles(
        {},
        "iam-admin-portal",
    )

    assert realm_roles == []
    assert client_roles == []


def test_missing_subject_is_rejected():
    with pytest.raises(
        TokenValidationError
    ) as exc_info:
        _validate_subject({})

    assert exc_info.value.reason == (
        "missing subject"
    )


def test_valid_subject_is_accepted():
    _validate_subject(
        {
            "sub": "keycloak-subject-123",
        }
    )


def test_missing_issuer_is_rejected():
    with pytest.raises(
        TokenValidationError
    ) as exc_info:
        _validate_issuer(
            {},
            (
                "http://localhost:8080"
                "/realms/novasecure"
            ),
        )

    assert exc_info.value.reason == (
        "missing issuer"
    )


def test_wrong_issuer_is_rejected():
    with pytest.raises(
        TokenValidationError
    ) as exc_info:
        _validate_issuer(
            {
                "iss": (
                    "http://evil.example"
                    "/realms/fake"
                )
            },
            (
                "http://localhost:8080"
                "/realms/novasecure"
            ),
        )

    assert exc_info.value.reason == (
        "invalid issuer"
    )


def test_valid_issuer_is_accepted():
    issuer = (
        "http://localhost:8080"
        "/realms/novasecure"
    )

    _validate_issuer(
        {
            "iss": issuer,
        },
        issuer,
    )


def test_string_audience_is_accepted():
    _validate_audience(
        {
            "aud": "iam-admin-portal",
        },
        "iam-admin-portal",
    )


def test_list_audience_is_accepted():
    _validate_audience(
        {
            "aud": [
                "account",
                "iam-admin-portal",
            ]
        },
        "iam-admin-portal",
    )


def test_wrong_audience_is_rejected():
    with pytest.raises(
        TokenValidationError
    ) as exc_info:
        _validate_audience(
            {
                "aud": "some-other-client",
            },
            "iam-admin-portal",
        )

    assert exc_info.value.reason == (
        "invalid_audience"
    )


def test_missing_audience_is_rejected():
    with pytest.raises(
        TokenValidationError
    ) as exc_info:
        _validate_audience(
            {},
            "iam-admin-portal",
        )

    assert exc_info.value.reason == (
        "missing audience"
    )