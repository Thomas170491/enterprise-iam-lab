import pytest
import services.role_service as role_service
from unittest.mock import Mock
from services.exceptions import RoleAdministrationPolicyError

def test_assign_identity_client(monkeypatch):
    role = {
        "id" : "role-uuid-123",
        "name" : "finance-data-viewer",
        "clientRole" : True,
    }

    monkeypatch.setattr(
        role_service,
        "get_client_uuid",
        lambda **kwargs : "client-uuid-123"
    )

    monkeypatch.setattr(
        role_service,
        "get_client_role",
        lambda **kwargs : role 
    )

    fake_assign = Mock()

    monkeypatch.setattr(
        role_service,
        "assign_client_role",
        fake_assign
    )

    result = role_service.assign_identity_client_role(
        admin_api_url= "https://keycloak.test/admin/realms/novasecure",
        token_url= "https://keycloak.test/token",
        client_id = "iam-governance-service",
        client_secret="fake-secret",
        user_id= "user-123",
        target_client_name="employee-portal",
        role_name="finance-data-viewer"

     )

    fake_assign.assert_called_once_with(
        admin_api_url="https://keycloak.test/admin/realms/novasecure",
        token_url="https://keycloak.test/token",
        client_id="iam-governance-service",
        client_secret="fake-secret",
        user_id="user-123",
        client_uuid="client-uuid-123",
        role=role,
    )

    assert result == {
        "user_id" : "user-123",
        "client_name" : "employee-portal",
        "role_id" : "role-uuid-123",
        "role_name" : "finance-data-viewer"

    }

def test_remove_identity_client_role(monkeypatch):
    role = {
        "id" : "role-uuid-123",
        "name" : "finance-data-viewer",
        "clientRole" : True,
    }

    monkeypatch.setattr(
        role_service,
        "get_client_uuid",
        lambda **kwargs : "client-uuid-123"
    )

    monkeypatch.setattr(
        role_service,
        "get_client_role",
        lambda **kwargs : role 
    )

    fake_remove = Mock()

    monkeypatch.setattr(
        role_service,
        "remove_client_role",
        fake_remove
    )

    result = role_service.remove_identity_client_role(
        admin_api_url= "https://keycloak.test/admin/realms/novasecure",
        token_url= "https://keycloak.test/token",
        client_id = "iam-governance-service",
        client_secret="fake-secret",
        user_id= "user-123",
        target_client_name="employee-portal",
        role_name="finance-data-viewer"

     )

    fake_remove.assert_called_once_with(
        admin_api_url="https://keycloak.test/admin/realms/novasecure",
        token_url="https://keycloak.test/token",
        client_id="iam-governance-service",
        client_secret="fake-secret",
        user_id="user-123",
        client_uuid="client-uuid-123",
        role=role,
    )

    assert result == {
        "user_id" : "user-123",
        "client_name" : "employee-portal",
        "role_id" : "role-uuid-123",
        "role_name" : "finance-data-viewer"

    }

def test_role_administration_rejects_unmanaged_client(
        monkeypatch,
):
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

            # Deliberately try to modify the
            # Governance Portal itself.
            target_client_name="iam-admin-portal",

            role_name="role-manager",
        )

    assert exc_info.value.reason == (
        "unmanaged client"
    )

    # Most important assertion:
    # Keycloak must not even be contacted.
    fake_client_lookup.assert_not_called()