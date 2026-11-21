from unittest.mock import Mock

import pytest

import services.remediation_service as remediation_service
from models import AccessReviewItem
from services.exceptions import KeycloakAdminAPIError

USER_ID = "5c6d7e8f-1a2b-4c3d-8e9f-0a1b2c3d4e5f"
ROLE_ID = "finance-role-id"
USER_GRANT = {
    "type": "user",
    "user_id": USER_ID,
    "assigned_role_id": ROLE_ID,
    "composite_path": [],
}
KEYCLOAK_ARGS = {
    "admin_api_url": "https://keycloak.test/admin/realms/novasecure",
    "token_url": "https://keycloak.test/token",
    "client_id": "iam-governance-service",
    "client_secret": "fake-secret",
}


def _item():
    """
    Build an unsaved captured item for the finance role held directly.
    """
    return AccessReviewItem(
        user_id=USER_ID,
        username="alice",
        client_name="employee-portal",
        role_id=ROLE_ID,
        role_name="finance-data-viewer",
        assignment_source="direct",
        grant_sources=[USER_GRANT],
    )


def test_get_live_access_assessment_reads_only_the_item_role(monkeypatch):
    """
    Verify that live access is read for the item's user and role only, then assessed.
    """
    fake_resolve = Mock(
        return_value=[
            {
                "role_id": ROLE_ID,
                "role_name": "finance-data-viewer",
                "assignment_source": "direct",
                "grant_sources": [USER_GRANT],
            }
        ]
    )
    monkeypatch.setattr(
        remediation_service, "resolve_user_client_role_sources", fake_resolve
    )

    result = remediation_service.get_live_access_assessment(_item(), **KEYCLOAK_ARGS)

    fake_resolve.assert_called_once_with(
        **KEYCLOAK_ARGS,
        user_id=USER_ID,
        target_client_name="employee-portal",
        role_ids={ROLE_ID},
    )
    assert result == {
        "drift": "none",
        "direct_grant_present": True,
        "other_grants_present": False,
    }
