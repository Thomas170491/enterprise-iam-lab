import pytest

from unittest.mock import Mock

import services.role_service as role_service

from services.exceptions import (
    AuditPersistenceError,
    KeycloakAdminAPIError,
    RoleAdministrationPolicyError,
)
from extensions import db
from models import ManagedRole

#Add application context
pytestmark = pytest.mark.usefixtures("app")


@pytest.fixture(autouse=True)
def managed_role_catalogue(app):
    """
    Seed enabled Employee Portal roles for each role-service test.
    """
    role_names = [
        "manager-dashboard",
        "hr-data-viewer",
        "finance-data-viewer",
        "it-data-viewer",
        "operations-data-viewer",
        "security-data-viewer",
    ]

    db.session.add_all([
        ManagedRole(
            client_name="employee-portal",
            role_name=role_name,
        )
        for role_name in role_names
    ])
    db.session.commit()
    
    
# ============================================================
# Shared test data
# ============================================================


def _fake_role():
    """
    Return a representative Keycloak client RoleRepresentation.
    """

    return {
        "id": "role-uuid-123",
        "name": "finance-data-viewer",
        "clientRole": True,
    }


def _patch_role_resolution(
        monkeypatch,
        role,
):
    """
    Replace the Keycloak client/role lookup operations.

    These tests exercise the Governance role service,
    not the real Keycloak Admin API.
    """
    
    monkeypatch.setattr(
        role_service,
        "get_effective_client_roles",
        lambda **kwargs : []
    )

    monkeypatch.setattr(
        role_service,
        "get_client_uuid",
        lambda **kwargs: "client-uuid-123",
    )

    monkeypatch.setattr(
        role_service,
        "get_client_role",
        lambda **kwargs: role,
    )

def test_get_managed_roles_returns_sorted_roles():
    """Return enabled catalogue role names in alphabetical order."""
    roles = role_service.get_managed_roles(
        "employee-portal"
    )

    assert roles == sorted(roles)

    assert "manager-dashboard" in roles
    assert "finance-data-viewer" in roles

def test_get_managed_roles_returns_empty_for_unmanaged_client():
    """Return no roles for a client outside the seeded catalogue."""
    roles = role_service.get_managed_roles(
        "iam-admin-portal"
    )

    assert roles == []


# ============================================================
# Assignment — successful path
# ============================================================


def test_assign_identity_client_role(monkeypatch):
    """Assign an allowed role and return its normalized representation."""
    role = _fake_role()

    _patch_role_resolution(
        monkeypatch,
        role,
    )
    


    fake_assign = Mock()

    monkeypatch.setattr(
        role_service,
        "assign_client_role",
        fake_assign,
    )

    # The real database must not be touched by this unit test.
    fake_audit = Mock()

    monkeypatch.setattr(
        role_service,
        "record_audit_event",
        fake_audit,
    )

    result = role_service.assign_identity_client_role(
        admin_api_url=(
            "https://keycloak.test/admin/realms/novasecure"
        ),
        token_url="https://keycloak.test/token",
        client_id="iam-governance-service",
        client_secret="fake-secret",
        user_id="user-123",
        target_client_name="employee-portal",
        role_name="finance-data-viewer",
        actor_user_id="leo-sub-123",
        actor_username="e1004",
    )

    fake_assign.assert_called_once_with(
        admin_api_url=(
            "https://keycloak.test/admin/realms/novasecure"
        ),
        token_url="https://keycloak.test/token",
        client_id="iam-governance-service",
        client_secret="fake-secret",
        user_id="user-123",
        client_uuid="client-uuid-123",
        role=role,
    )

    assert result == {
        "user_id": "user-123",
        "client_name": "employee-portal",
        "role_id": "role-uuid-123",
        "role_name": "finance-data-viewer",
    }


# ============================================================
# Removal — successful path
# ============================================================


def test_remove_identity_client_role(monkeypatch):
    """Remove a managed role and return its normalized representation."""
    role = _fake_role()

    _patch_role_resolution(
        monkeypatch,
        role,
    )

    fake_remove = Mock()

    monkeypatch.setattr(
        role_service,
        "remove_client_role",
        fake_remove,
    )

    fake_audit = Mock()

    monkeypatch.setattr(
        role_service,
        "record_audit_event",
        fake_audit,
    )

    result = role_service.remove_identity_client_role(
        admin_api_url=(
            "https://keycloak.test/admin/realms/novasecure"
        ),
        token_url="https://keycloak.test/token",
        client_id="iam-governance-service",
        client_secret="fake-secret",
        user_id="user-123",
        target_client_name="employee-portal",
        role_name="finance-data-viewer",
        actor_user_id="leo-sub-123",
        actor_username="e1004",
    )

    fake_remove.assert_called_once_with(
        admin_api_url=(
            "https://keycloak.test/admin/realms/novasecure"
        ),
        token_url="https://keycloak.test/token",
        client_id="iam-governance-service",
        client_secret="fake-secret",
        user_id="user-123",
        client_uuid="client-uuid-123",
        role=role,
    )

    assert result == {
        "user_id": "user-123",
        "client_name": "employee-portal",
        "role_id": "role-uuid-123",
        "role_name": "finance-data-viewer",
    }


# ============================================================
# Governance policy
# ============================================================


def test_role_administration_rejects_unmanaged_client(
        monkeypatch,
):
    """
    The Governance Portal must not be able to use this
    feature to modify its own administrative client roles.
    """

    fake_client_lookup = Mock()

    monkeypatch.setattr(
        role_service,
        "get_client_uuid",
        fake_client_lookup,
    )

    with pytest.raises(
        RoleAdministrationPolicyError
    ) as exc_info:

        role_service.assign_identity_client_role(
            admin_api_url=(
                "https://keycloak.test/admin/realms/novasecure"
            ),
            token_url="https://keycloak.test/token",
            client_id="iam-governance-service",
            client_secret="fake-secret",
            user_id="user-123",

            # Deliberately attempt to modify the
            # Governance Portal itself.
            target_client_name="iam-admin-portal",

            role_name="role-manager",
            actor_user_id="leo-sub-123",
            actor_username="e1004",
        )

    assert exc_info.value.reason == (
        "unmanaged_client"
    )

    # The request must be rejected before
    # Keycloak is ever contacted.
    fake_client_lookup.assert_not_called()


# ============================================================
# Assignment auditing
# ============================================================


def test_assign_identity_client_role_audits_human_actor(
        monkeypatch,
):
    """
    The human administrator must be recorded as the actor.

    iam-governance-service is only the technical executor.
    """

    role = _fake_role()

    _patch_role_resolution(
        monkeypatch,
        role,
    )

    monkeypatch.setattr(
        role_service,
        "assign_client_role",
        Mock(),
    )

    fake_audit = Mock()

    monkeypatch.setattr(
        role_service,
        "record_audit_event",
        fake_audit,
    )

    role_service.assign_identity_client_role(
        admin_api_url=(
            "https://keycloak.test/admin/realms/novasecure"
        ),
        token_url="https://keycloak.test/token",
        client_id="iam-governance-service",
        client_secret="fake-secret",
        user_id="target-user-123",
        target_client_name="employee-portal",
        role_name="finance-data-viewer",
        actor_user_id="leo-sub-123",
        actor_username="e1004",
    )

    # SoD evaluation, assignment attempt, and assignment success.
    assert fake_audit.call_count == 3

    sod_event = fake_audit.call_args_list[0].kwargs

    attempted_event = (
        fake_audit.call_args_list[1].kwargs
    )

    success_event = (
        fake_audit.call_args_list[2].kwargs
    )

    assert sod_event["action"] == "sod.evaluate"
    assert sod_event["outcome"] == "allow"
    assert sod_event["details"]["reason"] == "no_sod_conflict"
    assert sod_event["details"]["rule_id"] is None
    assert sod_event["details"]["requested_role"] == "finance-data-viewer"
    assert sod_event["details"]["current_roles"] == []
    for event in (sod_event, attempted_event, success_event):
        assert event["actor_user_id"] == "leo-sub-123"
        assert event["actor_username"] == "e1004"
        assert event["target_id"] == "target-user-123"
        assert event["details"]["service_client"] == "iam-governance-service"
        assert event["details"]["client_name"] == "employee-portal"
    assert success_event["action"] == "role.assign"

    assert attempted_event[
        "actor_user_id"
    ] == "leo-sub-123"

    assert attempted_event[
        "actor_username"
    ] == "e1004"

    assert attempted_event[
        "action"
    ] == "role.assign"

    assert attempted_event[
        "target_id"
    ] == "target-user-123"

    assert attempted_event[
        "outcome"
    ] == "attempted"

    assert attempted_event[
        "details"
    ]["service_client"] == (
        "iam-governance-service"
    )

    assert attempted_event[
        "details"
    ]["client_name"] == (
        "employee-portal"
    )

    assert attempted_event[
        "details"
    ]["role_name"] == (
        "finance-data-viewer"
    )

    assert success_event[
        "outcome"
    ] == "success"


# ============================================================
# Removal auditing
# ============================================================


def test_remove_identity_client_role_audits_human_actor(
        monkeypatch,
):
    """Record the human actor and service client for role removal."""
    role = _fake_role()

    _patch_role_resolution(
        monkeypatch,
        role,
    )

    monkeypatch.setattr(
        role_service,
        "remove_client_role",
        Mock(),
    )

    fake_audit = Mock()

    monkeypatch.setattr(
        role_service,
        "record_audit_event",
        fake_audit,
    )

    role_service.remove_identity_client_role(
        admin_api_url=(
            "https://keycloak.test/admin/realms/novasecure"
        ),
        token_url="https://keycloak.test/token",
        client_id="iam-governance-service",
        client_secret="fake-secret",
        user_id="target-user-123",
        target_client_name="employee-portal",
        role_name="finance-data-viewer",
        actor_user_id="leo-sub-123",
        actor_username="e1004",
    )

    assert fake_audit.call_count == 2

    attempted_event = (
        fake_audit.call_args_list[0].kwargs
    )

    success_event = (
        fake_audit.call_args_list[1].kwargs
    )

    assert attempted_event[
        "actor_user_id"
    ] == "leo-sub-123"

    assert attempted_event[
        "actor_username"
    ] == "e1004"

    assert attempted_event[
        "action"
    ] == "role.remove"

    assert attempted_event[
        "outcome"
    ] == "attempted"

    assert attempted_event[
        "details"
    ]["service_client"] == (
        "iam-governance-service"
    )

    assert success_event[
        "outcome"
    ] == "success"


# ============================================================
# Fail closed — assignment
# ============================================================


def test_assignment_not_performed_when_initial_audit_fails(
        monkeypatch,
):
    """
    Privileged mutations must fail closed.

    If the initial audit event cannot be persisted,
    Keycloak must remain unchanged.
    """

    role = _fake_role()

    _patch_role_resolution(
        monkeypatch,
        role,
    )

    fake_assign = Mock()

    monkeypatch.setattr(
        role_service,
        "assign_client_role",
        fake_assign,
    )

    monkeypatch.setattr(
        role_service,
        "record_audit_event",
        Mock(
            side_effect=AuditPersistenceError(
                "database unavailable"
            )
        ),
    )

    with pytest.raises(
        AuditPersistenceError
    ):
        role_service.assign_identity_client_role(
            admin_api_url=(
                "https://keycloak.test/admin/realms/novasecure"
            ),
            token_url="https://keycloak.test/token",
            client_id="iam-governance-service",
            client_secret="fake-secret",
            user_id="target-user-123",
            target_client_name="employee-portal",
            role_name="finance-data-viewer",
            actor_user_id="leo-sub-123",
            actor_username="e1004",
        )

    fake_assign.assert_not_called()


# ============================================================
# Fail closed — removal
# ============================================================


def test_removal_not_performed_when_initial_audit_fails(
        monkeypatch,
):
    """Prevent removal when its initial audit event cannot be saved."""
    role = _fake_role()

    _patch_role_resolution(
        monkeypatch,
        role,
    )

    fake_remove = Mock()

    monkeypatch.setattr(
        role_service,
        "remove_client_role",
        fake_remove,
    )

    monkeypatch.setattr(
        role_service,
        "record_audit_event",
        Mock(
            side_effect=AuditPersistenceError(
                "database unavailable"
            )
        ),
    )

    with pytest.raises(
        AuditPersistenceError
    ):
        role_service.remove_identity_client_role(
            admin_api_url=(
                "https://keycloak.test/admin/realms/novasecure"
            ),
            token_url="https://keycloak.test/token",
            client_id="iam-governance-service",
            client_secret="fake-secret",
            user_id="target-user-123",
            target_client_name="employee-portal",
            role_name="finance-data-viewer",
            actor_user_id="leo-sub-123",
            actor_username="e1004",
        )

    fake_remove.assert_not_called()


# ============================================================
# Keycloak assignment failure
# ============================================================


def test_assignment_failure_is_audited(
        monkeypatch,
):
    """Record SoD approval, assignment attempt, and Keycloak failure."""
    role = _fake_role()

    _patch_role_resolution(
        monkeypatch,
        role,
    )

    monkeypatch.setattr(
        role_service,
        "assign_client_role",
        Mock(
            side_effect=KeycloakAdminAPIError(
                "Client role assignment failed"
            )
        ),
    )

    fake_audit = Mock()

    monkeypatch.setattr(
        role_service,
        "record_audit_event",
        fake_audit,
    )

    with pytest.raises(
        KeycloakAdminAPIError
    ):
        role_service.assign_identity_client_role(
            admin_api_url=(
                "https://keycloak.test/admin/realms/novasecure"
            ),
            token_url="https://keycloak.test/token",
            client_id="iam-governance-service",
            client_secret="fake-secret",
            user_id="target-user-123",
            target_client_name="employee-portal",
            role_name="finance-data-viewer",
            actor_user_id="leo-sub-123",
            actor_username="e1004",
        )

    assert fake_audit.call_count == 3

    assert [
        (entry.kwargs["action"], entry.kwargs["outcome"])
        for entry in fake_audit.call_args_list
    ] == [
        ("sod.evaluate", "allow"),
        ("role.assign", "attempted"),
        ("role.assign", "failure"),
    ]


# ============================================================
# Keycloak removal failure
# ============================================================


def test_removal_failure_is_audited(
        monkeypatch,
):
    """Record the attempt and failure when Keycloak rejects removal."""
    role = _fake_role()

    _patch_role_resolution(
        monkeypatch,
        role,
    )

    monkeypatch.setattr(
        role_service,
        "remove_client_role",
        Mock(
            side_effect=KeycloakAdminAPIError(
                "Client role removal failed"
            )
        ),
    )

    fake_audit = Mock()

    monkeypatch.setattr(
        role_service,
        "record_audit_event",
        fake_audit,
    )

    with pytest.raises(
        KeycloakAdminAPIError
    ):
        role_service.remove_identity_client_role(
            admin_api_url=(
                "https://keycloak.test/admin/realms/novasecure"
            ),
            token_url="https://keycloak.test/token",
            client_id="iam-governance-service",
            client_secret="fake-secret",
            user_id="target-user-123",
            target_client_name="employee-portal",
            role_name="finance-data-viewer",
            actor_user_id="leo-sub-123",
            actor_username="e1004",
        )

    assert fake_audit.call_count == 2

    assert (
        fake_audit.call_args_list[0]
        .kwargs["outcome"]
        == "attempted"
    )

    assert (
        fake_audit.call_args_list[1]
        .kwargs["outcome"]
        == "failure"
    )


# ============================================================
# Final audit failure must not undo successful assignment
# ============================================================


def test_assignment_success_not_masked_by_final_audit_failure(
        monkeypatch,
):
    """
    If Keycloak successfully assigns the role but the final
    'success' audit record fails, the service must not report
    the Keycloak mutation itself as failed.

    The earlier 'attempted' record already exists.
    """

    role = _fake_role()

    _patch_role_resolution(
        monkeypatch,
        role,
    )

    fake_assign = Mock()

    monkeypatch.setattr(
        role_service,
        "assign_client_role",
        fake_assign,
    )

    fake_audit = Mock(
        side_effect=[
            None,
            None,
            AuditPersistenceError(
                "database unavailable"
            ),
        ]
    )

    monkeypatch.setattr(
        role_service,
        "record_audit_event",
        fake_audit,
    )

    result = role_service.assign_identity_client_role(
        admin_api_url=(
            "https://keycloak.test/admin/realms/novasecure"
        ),
        token_url="https://keycloak.test/token",
        client_id="iam-governance-service",
        client_secret="fake-secret",
        user_id="target-user-123",
        target_client_name="employee-portal",
        role_name="finance-data-viewer",
        actor_user_id="leo-sub-123",
        actor_username="e1004",
    ) 

    fake_assign.assert_called_once()

    assert result["role_name"] == (
        "finance-data-viewer"
    )
    assert fake_audit.call_count == 3


# ============================================================
# Final audit failure must not undo successful removal
# ============================================================


def test_removal_success_not_masked_by_final_audit_failure(
        monkeypatch,
):
    """Preserve successful removal when its final audit write fails."""
    role = _fake_role()

    _patch_role_resolution(
        monkeypatch,
        role,
    )

    fake_remove = Mock()

    monkeypatch.setattr(
        role_service, 
        "remove_client_role",
        fake_remove,
    )

    fake_audit = Mock(
        side_effect=[
            None,
            AuditPersistenceError(
                "database unavailable"
            ),
        ]
    )

    monkeypatch.setattr(
        role_service,
        "record_audit_event",
        fake_audit,
    )

    result = role_service.remove_identity_client_role(
        admin_api_url=(
            "https://keycloak.test/admin/realms/novasecure"
        ),
        token_url="https://keycloak.test/token",
        client_id="iam-governance-service",
        client_secret="fake-secret",
        user_id="target-user-123",
        target_client_name="employee-portal",
        role_name="finance-data-viewer",
        actor_user_id="leo-sub-123",
        actor_username="e1004",
    )

    fake_remove.assert_called_once()

    assert result["role_name"] == (
        "finance-data-viewer"
    )

    assert fake_audit.call_count == 2

def test_role_administration_rejects_unmanaged_role(monkeypatch):
    """Reject an unlisted role before contacting Keycloak."""

    fake_client_lookup = Mock()

    monkeypatch.setattr( 
        role_service,
        "get_client_uuid",
        fake_client_lookup,
    )
    with pytest.raises(
        RoleAdministrationPolicyError
    ) as exc_info:
        
        role_service.assign_identity_client_role(
            admin_api_url=(
                "https://keycloak.test/admin/realms/novasecure"
            ),
            token_url="https://keycloak.test/token",
            client_id="iam-governance-service",
            client_secret="fake-secret",
            user_id="user-123",
            target_client_name="employee-portal",

            # Deliberately not in MANAGED_ROLES.
            role_name="portal-user",

            actor_user_id="leo-sub-123",
            actor_username="e1004",
        )

    assert exc_info.value.reason == "unmanaged_role"
    fake_client_lookup.assert_not_called()

def test_role_administration_rejects_unmanaged_role_removal(monkeypatch):
        """Reject removal of an unlisted role before contacting Keycloak."""

        fake_client_lookup = Mock()

        monkeypatch.setattr(
            role_service,
            "get_client_uuid",
            fake_client_lookup,
        )
        with pytest.raises(
            RoleAdministrationPolicyError
        ) as exc_info:
            
            role_service.remove_identity_client_role(
                admin_api_url=(
                    "https://keycloak.test/admin/realms/novasecure"
                ),
                token_url="https://keycloak.test/token",
                client_id="iam-governance-service",
                client_secret="fake-secret",
                user_id="user-123",
                target_client_name="employee-portal",

                # Deliberately not in MANAGED_ROLES.
                role_name="portal-user",

                actor_user_id="leo-sub-123",
                actor_username="e1004",
            )

        assert exc_info.value.reason == "unmanaged_role"
        fake_client_lookup.assert_not_called()
            
def test_sod_deny_prevents_keycloak_assignment(monkeypatch):
    """
    Verify that an SoD deny decision prevents the Keycloak assignment.
    """
    
    fake_assign = Mock()
    
    monkeypatch.setattr(
        role_service,
        "get_effective_client_roles",
        lambda **kwargs :[{
            "id" : "finance-role-id",
            "name" : "finance-data-viewer"            
        }]
    )
    
    monkeypatch.setattr(
        role_service,
        "assign_client_role",
        fake_assign
    )
    
    monkeypatch.setattr(
        role_service,
        "evaluate_role_assignment",
        lambda **kwargs : {
            "decision" : "deny",
            "reason" : "sod_rule_matched",
            "rule_id" : 1
        } 
    )
    
    with pytest.raises(
        RoleAdministrationPolicyError
    ) as exc_info:
        role_service.assign_identity_client_role(
            admin_api_url="https://keycloak.test/admin",
            token_url="https://keycloak.test/token",
            client_id="iam-governance-service",
            client_secret="test-secret",
            user_id="user-123",
            target_client_name="employee-portal",
            role_name="security-data-viewer",
            actor_user_id="operator-123",
            actor_username="leo",
        )

    
    assert exc_info.value.reason == "sod_deny"
    fake_assign.assert_not_called()
    
def test_sod_review_prevents_immediate_keycloak_assignment(monkeypatch):
    
    """
    Verify that an SoD review decision prevents immediate assignment.
    """
    
    fake_assign = Mock()
    
    monkeypatch.setattr(
        role_service,
        "get_effective_client_roles",
        lambda **kwargs :[{
            "id" : "finance-role-id",
            "name" : "finance-data-viewer"            
        }]
    )
    
    monkeypatch.setattr(
        role_service,
        "assign_client_role",
        fake_assign
    )
    
    monkeypatch.setattr(
        role_service,
        "evaluate_role_assignment",
        lambda **kwargs : {
            "decision" : "requires_review",
            "reason" : "sod_rule_matched",
            "rule_id" : 1
        } 
    )
    
    with pytest.raises(
        RoleAdministrationPolicyError
    ) as exc_info:
        role_service.assign_identity_client_role(
            admin_api_url="https://keycloak.test/admin",
            token_url="https://keycloak.test/token",
            client_id="iam-governance-service",
            client_secret="test-secret",
            user_id="user-123",
            target_client_name="employee-portal",
            role_name="security-data-viewer",
            actor_user_id="operator-123",
            actor_username="leo",
        )

    
    assert exc_info.value.reason == "sod_requires_review"
    fake_assign.assert_not_called()
    
def test_assignment_not_performed_when_attempt_audit_fails(monkeypatch):
    """
    Prevent assignment when its attempt audit fails after SoD auditing succeeds.
    """

    role = _fake_role()

    _patch_role_resolution(
        monkeypatch,
        role,
    )

    fake_assign = Mock()

    monkeypatch.setattr(
        role_service,
        "assign_client_role",
        fake_assign,
    )

    monkeypatch.setattr(
        role_service,
        "record_audit_event",
        Mock(
            None, 
            side_effect=AuditPersistenceError(
                "database unavailable"
            )
        ),
    )

    with pytest.raises(
        AuditPersistenceError
    ):
        role_service.assign_identity_client_role(
            admin_api_url=(
                "https://keycloak.test/admin/realms/novasecure"
            ),
            token_url="https://keycloak.test/token",
            client_id="iam-governance-service",
            client_secret="fake-secret",
            user_id="target-user-123",
            target_client_name="employee-portal",
            role_name="finance-data-viewer",
            actor_user_id="leo-sub-123",
            actor_username="e1004",
        )

    fake_assign.assert_not_called()
    
    