import pytest
from unittest.mock import Mock

from extensions import db
from models import AccessReview, AccessReviewItem, ManagedRole
import services.access_review_service as access_review_service

create_access_review = access_review_service.create_access_review


def _resolved_direct_role(role_id: str, role_name: str) -> dict:
    """Build a direct role with the user grant evidence used by capture tests."""
    return {
        "role_id": role_id,
        "role_name": role_name,
        "assignment_source": "direct",
        "grant_sources": [
            {
                "type": "user",
                "user_id": "user-123",
                "assigned_role_id": role_id,
                "composite_path": [],
            }
        ],
    }


def test_populate_access_review_captures_managed_direct_role(monkeypatch, app):
    """
    Verify that a managed direct role is captured in a manager-owned draft campaign.
    """

    campaign = create_access_review("test campaign", "manager-123", "reviewer-456")

    managed_role = ManagedRole(
        client_name="employee-portal", role_name="finance-data-viewer", enabled=True
    )

    db.session.add(managed_role)
    db.session.flush()

    fake_get_user = Mock(return_value={"id": "user-123", "username": "alice"})
    fake_resolve_roles = Mock(
        return_value=[_resolved_direct_role("finance-role-id", "finance-data-viewer")]
    )

    monkeypatch.setattr(access_review_service, "get_user", fake_get_user)

    monkeypatch.setattr(
        access_review_service, "resolve_user_client_role_sources", fake_resolve_roles
    )

    created_items = access_review_service.populate_access_review_from_identity(
        review_id=campaign.id,
        manager_user_id="manager-123",
        user_id="user-123",
        admin_api_url="https://keycloak.test/admin",
        token_url="https://keycloak.test/token",
        client_id="iam-governance-service",
        client_secret="test-secret",
    )

    assert len(created_items) == 1

    item = created_items[0]

    assert item.id is not None
    assert item.review_id == campaign.id
    assert item.user_id == "user-123"
    assert item.username == "alice"
    assert item.client_name == "employee-portal"
    assert item.role_id == "finance-role-id"
    assert item.role_name == "finance-data-viewer"
    assert item.assignment_source == "direct"
    assert item.grant_sources == _resolved_direct_role(
        "finance-role-id", "finance-data-viewer"
    )["grant_sources"]


def test_populate_access_review_skips_existing_items(app, monkeypatch):
    """
    Verify that repeated population does not duplicate captured access items.
    """
    campaign = create_access_review(
        "test campaign",
        "manager-123",
        "reviewer-456",
    )

    managed_role = ManagedRole(
        client_name="employee-portal",
        role_name="finance-data-viewer",
        enabled=True,
    )
    db.session.add(managed_role)
    db.session.flush()

    monkeypatch.setattr(
        access_review_service,
        "get_user",
        Mock(
            return_value={
                "id": "user-123",
                "username": "alice",
            }
        ),
    )

    monkeypatch.setattr(
        access_review_service,
        "resolve_user_client_role_sources",
        Mock(
            return_value=[
                _resolved_direct_role("finance-role-id", "finance-data-viewer")
            ]
        ),
    )

    arguments = {
        "review_id": campaign.id,
        "manager_user_id": "manager-123",
        "user_id": "user-123",
        "admin_api_url": "https://keycloak.test/admin",
        "token_url": "https://keycloak.test/token",
        "client_id": "iam-governance-service",
        "client_secret": "test-secret",
    }

    first_items = access_review_service.populate_access_review_from_identity(
        **arguments
    )
    second_items = access_review_service.populate_access_review_from_identity(
        **arguments
    )

    assert len(first_items) == 1
    assert second_items == []

    saved_items = (
        db.session.execute(
            db.select(AccessReviewItem).where(
                AccessReviewItem.review_id == campaign.id,
            )
        )
        .scalars()
        .all()
    )

    assert len(saved_items) == 1
    assert saved_items[0].id == first_items[0].id


def test_populate_access_review_rejects_other_manager(app, monkeypatch):
    """
    Verify that another manager cannot populate a campaign or trigger Keycloak lookups.
    """
    campaign = create_access_review(
        "test campaign",
        "manager-123",
        "reviewer-456",
    )

    fake_get_user = Mock()
    fake_get_roles = Mock()

    monkeypatch.setattr(
        access_review_service,
        "get_user",
        fake_get_user,
    )

    monkeypatch.setattr(
        access_review_service,
        "resolve_user_client_role_sources",
        fake_get_roles,
    )

    with pytest.raises(ValueError, match="access_review_not_found"):
        access_review_service.populate_access_review_from_identity(
            review_id=campaign.id,
            manager_user_id="other-manager",
            user_id="user-123",
            admin_api_url="https://keycloak.test/admin",
            token_url="https://keycloak.test/token",
            client_id="iam-governance-service",
            client_secret="test-secret",
        )

    fake_get_user.assert_not_called()
    fake_get_roles.assert_not_called()

    saved_items = (
        db.session.execute(
            db.select(AccessReviewItem).where(
                AccessReviewItem.review_id == campaign.id,
            )
        )
        .scalars()
        .all()
    )

    assert saved_items == []


@pytest.mark.parametrize("status", ["open", "completed", "cancelled"])
def test_populate_access_review_rejects_non_draft_campaign(app, monkeypatch, status):
    """
    Verify that non-draft campaigns reject population before Keycloak lookups.
    """
    campaign = create_access_review(
        "test campaign",
        "manager-123",
        "reviewer-456",
    )

    campaign.status = status
    db.session.flush()

    fake_get_user = Mock()
    fake_get_roles = Mock()

    monkeypatch.setattr(
        access_review_service,
        "get_user",
        fake_get_user,
    )

    monkeypatch.setattr(
        access_review_service,
        "resolve_user_client_role_sources",
        fake_get_roles,
    )
    with pytest.raises(ValueError, match="access_review_not_draft"):
        result = access_review_service.populate_access_review_from_identity(
            review_id=campaign.id,
            manager_user_id="manager-123",
            user_id="user-123",
            admin_api_url="https://keycloak.test/admin",
            token_url="https://keycloak.test/token",
            client_id="iam-governance-service",
            client_secret="test-secret",
        )

        fake_get_user.assert_not_called()
        fake_get_roles.assert_not_called()
        assert (
            db.session.execute(
                db.select(AccessReviewItem).where(
                    AccessReviewItem.review_id == campaign.id,
                )
            )
            .scalars()
            .all()
            == []
        )


def test_populate_access_review_skips_unmanaged_roles(app, monkeypatch):
    """
    Verify that population captures managed roles and skips unmanaged effective roles.
    """
    campaign = create_access_review(
        "test campaign",
        "manager-123",
        "reviewer-456",
    )

    managed_role = ManagedRole(
        client_name="employee-portal",
        role_name="finance-data-viewer",
        enabled=True,
    )
    db.session.add(managed_role)
    db.session.flush()

    monkeypatch.setattr(
        access_review_service,
        "get_user",
        Mock(
            return_value={
                "id": "user-123",
                "username": "alice",
            }
        ),
    )

    monkeypatch.setattr(
        access_review_service,
        "resolve_user_client_role_sources",
        Mock(
            return_value=[
                _resolved_direct_role("portal-role-id", "portal-user"),
                _resolved_direct_role("finance-role-id", "finance-data-viewer"),
            ]
        ),
    )

    created_items = access_review_service.populate_access_review_from_identity(
        review_id=campaign.id,
        manager_user_id="manager-123",
        user_id="user-123",
        admin_api_url="https://keycloak.test/admin",
        token_url="https://keycloak.test/token",
        client_id="iam-governance-service",
        client_secret="test-secret",
    )

    assert len(created_items) == 1
    assert created_items[0].role_name == "finance-data-viewer"
    assert created_items[0].role_id == "finance-role-id"

    saved_items = (
        db.session.execute(
            db.select(AccessReviewItem).where(
                AccessReviewItem.review_id == campaign.id,
            )
        )
        .scalars()
        .all()
    )

    assert len(saved_items) == 1
    assert saved_items[0].id == created_items[0].id
    assert saved_items[0].role_name == "finance-data-viewer"


def test_populate_access_review_does_not_commit(app, monkeypatch):
    """
    Verify that captured access items can be rolled back while the campaign remains saved.
    """
    campaign = create_access_review(
        "test campaign",
        "manager-123",
        "reviewer-456",
    )

    managed_role = ManagedRole(
        client_name="employee-portal",
        role_name="finance-data-viewer",
        enabled=True,
    )
    db.session.add(managed_role)
    db.session.commit()

    campaign_id = campaign.id

    monkeypatch.setattr(
        access_review_service,
        "get_user",
        Mock(
            return_value={
                "id": "user-123",
                "username": "alice",
            }
        ),
    )

    monkeypatch.setattr(
        access_review_service,
        "resolve_user_client_role_sources",
        Mock(
            return_value=[
                _resolved_direct_role("finance-role-id", "finance-data-viewer")
            ]
        ),
    )

    created_items = access_review_service.populate_access_review_from_identity(
        review_id=campaign_id,
        manager_user_id="manager-123",
        user_id="user-123",
        admin_api_url="https://keycloak.test/admin",
        token_url="https://keycloak.test/token",
        client_id="iam-governance-service",
        client_secret="test-secret",
    )

    assert len(created_items) == 1
    assert created_items[0].id is not None

    db.session.rollback()

    saved_campaign = db.session.get(AccessReview, campaign_id)
    assert saved_campaign is not None
    assert saved_campaign.status == "draft"

    saved_items = (
        db.session.execute(
            db.select(AccessReviewItem).where(
                AccessReviewItem.review_id == campaign_id,
            )
        )
        .scalars()
        .all()
    )

    assert saved_items == []


def test_populate_access_review_captures_managed_inherited_role_with_sources(
    monkeypatch, app
):
    """
    Verify that capture saves an inherited managed role and its group evidence.
    """

    campaign = create_access_review(
        name="Finance review",
        created_by_user_id="manager-123",
        reviewer_user_id="reviewer-456",
    )

    db.session.add(
        ManagedRole(
            client_name="employee-portal",
            role_name="finance-data-viewer",
            enabled=True,
        )
    )
    db.session.flush()

    group_grant = {
        "type": "group",
        "group_id": "finance-id",
        "membership_group_id": "finance-team-id",
        "assigned_role_id": "finance-staff-id",
        "composite_path": ["finance-staff-id", "finance-viewer-id"],
    }
    resolved_role = {
        "role_id": "finance-viewer-id",
        "role_name": "finance-data-viewer",
        "assignment_source": "inherited",
        "grant_sources": [group_grant],
    }

    monkeypatch.setattr(
        access_review_service,
        "get_user",
        Mock(return_value={"id": "user-123", "username": "alice"}),
    )
    monkeypatch.setattr(
        access_review_service,
        "resolve_user_client_role_sources",
        Mock(return_value=[resolved_role]),
    )

    created_items = access_review_service.populate_access_review_from_identity(
        review_id=campaign.id,
        manager_user_id="manager-123",
        user_id="user-123",
        admin_api_url="https://keycloak.test/admin/realms/novasecure",
        token_url="https://keycloak.test/token",
        client_id="iam-governance-service",
        client_secret="test-secret",
    )

    assert len(created_items) == 1
    item = created_items[0]
    assert item.review_id == campaign.id
    assert item.role_id == "finance-viewer-id"
    assert item.role_name == "finance-data-viewer"
    assert item.assignment_source == "inherited"
    assert item.grant_sources == [group_grant]
    
def test_populate_access_review_captures_both_user_and_group_sources(monkeypatch, app):
    """
    Verify that a captured role retains both its user and group grant evidence.
    """
    
    enabled_role = ManagedRole(
        client_name="employee-portal",
        role_name="finance-data-viewer",
        enabled=True,
    )
    
    campaign = create_access_review(
        name="Finance review",
        created_by_user_id="manager-123",
        reviewer_user_id="reviewer-456",
    )
    db.session.add(enabled_role)
    db.session.flush()
    
    resolved_role = {
        "role_id": "finance-viewer-id",
        "role_name": "finance-data-viewer",
        "assignment_source": "both",
        "grant_sources": [
            {
                "type": "user",
                "user_id": "user-123",
                "assigned_role_id": "finance-viewer-id",
                "composite_path": [],
            },
            {
                "type": "group",
                "group_id": "finance-id",
                "membership_group_id": "finance-team-id",
                "assigned_role_id": "finance-staff-id",
                "composite_path": ["finance-staff-id", "finance-viewer-id"],
            },
        ],
    }
    
    monkeypatch.setattr(
        access_review_service,
        "resolve_user_client_role_sources",
        Mock(return_value=[resolved_role]),
    )
    
    monkeypatch.setattr(
        access_review_service,
        "get_user",
        Mock(return_value={"id": "user-123", "username": "alice"}),
    )
    
    created_items = access_review_service.populate_access_review_from_identity(
        review_id=campaign.id,
        manager_user_id="manager-123",
        user_id="user-123",
        admin_api_url="https://keycloak.test/admin/realms/novasecure",
        token_url="https://keycloak.test/token",
        client_id="iam-governance-service",
        client_secret="test-secret",
    )
    
    assert len(created_items) == 1
    item = created_items[0]

    assert item.role_id == resolved_role["role_id"]
    assert item.assignment_source == "both"
    assert item.grant_sources == resolved_role["grant_sources"]
    assert {grant["type"] for grant in item.grant_sources} == {"user", "group"}
    


