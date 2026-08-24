from types import SimpleNamespace
import pytest 
from werkzeug.exceptions import Forbidden

import auth.decorators as decorators

from auth.permissions import (
    ACCESS_REVIEWER,
    AUDIT_LOG_VIEWER,
    IAM_DASHBOARD_ACCESS,
    IDENTITY_MANAGER,
    IDENTITY_VIEWER,
    REPORT_EXPORTER,
    ROLE_MANAGER,
)


# ---------------------------------------------------------
# Test-only NovaSecure personas
# ---------------------------------------------------------
#
# These are not application authorization rules.
# Keycloak remains the real source of role assignments.
#
# The personas simply let our test suite verify the
# authorization boundaries we designed.
# ---------------------------------------------------------

LEO_ROLES= [
        IAM_DASHBOARD_ACCESS,
    IDENTITY_VIEWER,
    IDENTITY_MANAGER,
    ROLE_MANAGER,
    REPORT_EXPORTER,
]


EMMA_ROLES = [
    IAM_DASHBOARD_ACCESS,
    IDENTITY_VIEWER,
    ACCESS_REVIEWER,
    AUDIT_LOG_VIEWER,
    REPORT_EXPORTER,
]

NADIA_ROLES = [
    IAM_DASHBOARD_ACCESS,
    IDENTITY_VIEWER,
    AUDIT_LOG_VIEWER,
]

ALICE_ROLES = []

def _run_protected_view(
        monkeypatch,
        user_roles,
        required_role,
) :

    """
    Execute a view protected by client_role_required()
    using a fake authenticated user.
    """

    fake_user = SimpleNamespace(client_roles = user_roles)

    monkeypatch.setattr(
        decorators,
        "current_user",
        fake_user
    )

    @decorators.client_role_required(required_role)

    def protected_view() :
        return "allowed"
    
    return protected_view()

@pytest.mark.parametrize(
    "role",
    [
        IAM_DASHBOARD_ACCESS,
        IDENTITY_VIEWER,
        IDENTITY_MANAGER,
        ROLE_MANAGER,
        REPORT_EXPORTER,
    ]
)

def test_leo_has_operator_permissions(
    monkeypatch,
    role
) :
 result = _run_protected_view(
        monkeypatch,
        LEO_ROLES,
        role,
    )

 assert result == "allowed"


@pytest.mark.parametrize(
    "role",
    [
        IAM_DASHBOARD_ACCESS,
        IDENTITY_VIEWER,
        ACCESS_REVIEWER,
        AUDIT_LOG_VIEWER,
        REPORT_EXPORTER,
    ],
)
def test_emma_has_auditor_permissions(
    monkeypatch,
    role,
):
    result = _run_protected_view(
        monkeypatch,
        EMMA_ROLES,
        role,
    )

    assert result == "allowed"


@pytest.mark.parametrize(
    "role",
    [
        IAM_DASHBOARD_ACCESS,
        IDENTITY_VIEWER,
        AUDIT_LOG_VIEWER,
    ],
)
def test_nadia_has_security_permissions(
    monkeypatch,
    role,
):
    result = _run_protected_view(
        monkeypatch,
        NADIA_ROLES,
        role,
    )

    assert result == "allowed"

@pytest.mark.parametrize(
    "role",
    [
        ACCESS_REVIEWER,
        AUDIT_LOG_VIEWER,
    ],
)
def test_leo_cannot_perform_auditor_functions(
    monkeypatch,
    role,
):
    with pytest.raises(Forbidden):
        _run_protected_view(
            monkeypatch,
            LEO_ROLES,
            role,
        )

@pytest.mark.parametrize(
    "role",
    [
        IDENTITY_MANAGER,
        ROLE_MANAGER,
    ],
)
def test_emma_cannot_administer_access(
    monkeypatch,
    role,
):
    with pytest.raises(Forbidden):
        _run_protected_view(
            monkeypatch,
            EMMA_ROLES,
            role,
        )

@pytest.mark.parametrize(
    "role",
    [
        IDENTITY_MANAGER,
        ROLE_MANAGER,
        ACCESS_REVIEWER,
        REPORT_EXPORTER,
    ],
)
def test_nadia_cannot_modify_or_certify_access(
    monkeypatch,
    role,
):
    with pytest.raises(Forbidden):
        _run_protected_view(
            monkeypatch,
            NADIA_ROLES,
            role,
        )

@pytest.mark.parametrize(
    "role",
    [
        IAM_DASHBOARD_ACCESS,
        IDENTITY_VIEWER,
        IDENTITY_MANAGER,
        ROLE_MANAGER,
        ACCESS_REVIEWER,
        AUDIT_LOG_VIEWER,
        REPORT_EXPORTER,
    ],
)
def test_alice_has_no_governance_permissions(
    monkeypatch,
    role,
):
    with pytest.raises(Forbidden):
        _run_protected_view(
            monkeypatch,
            ALICE_ROLES,
            role,
        )
