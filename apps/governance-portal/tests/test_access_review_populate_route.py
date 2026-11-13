from unittest.mock import Mock

import pytest
import requests
from sqlalchemy.exc import SQLAlchemyError

from auth.permissions import ACCESS_REVIEW_MANAGER, ACCESS_REVIEWER
from extensions import db
from models import AccessReviewItem, AuditEvent, ManagedRole
from services.exceptions import AuditPersistenceError, KeycloakAdminAPIError
from tests.access_review_helpers import _login_user

import governance.routes as governance_routes
import services.access_review_service as access_review_service
import services.keycloak_auth_service as keycloak_auth_service


def test_manager_can_populate_own_access_review(client, monkeypatch):
    """
    Verify that a manager can capture access in their campaign and receives the correct redirect.
    """
    _login_user(client, [ACCESS_REVIEW_MANAGER])

    campaign = access_review_service.create_access_review(
        "test campaign",
        "test-subject",
        "user-456",
    )

    db.session.add(
        ManagedRole(
            client_name="employee-portal",
            role_name="finance-data-viewer",
            enabled=True,
        )
    )
    db.session.flush()

    monkeypatch.setattr(
        access_review_service,
        "get_user",
        lambda **kwargs: {
            "id": "3f2b8c1e-5d4a-4e6f-9a7b-1c2d3e4f5a6b",
            "username": "alice",
        },
    )
    monkeypatch.setattr(
        access_review_service,
        "resolve_user_client_role_sources",
        lambda **kwargs: [{
            "role_id": "finance-role-id",
            "role_name": "finance-data-viewer",
            "assignment_source": "direct",
            "grant_sources": [{
                "type": "user",
                "user_id": "3f2b8c1e-5d4a-4e6f-9a7b-1c2d3e4f5a6b",
                "assigned_role_id": "finance-role-id",
                "composite_path": [],
            }],
        }],
    )

    response = client.post(
        f"/access-reviews/manage/{campaign.id}/populate",
        data={"user_id": "3f2b8c1e-5d4a-4e6f-9a7b-1c2d3e4f5a6b"},
    )

    assert response.status_code == 303
    assert response.headers["Location"] == f"/access-reviews/manage/{campaign.id}"

    item = db.session.execute(
        db.select(AccessReviewItem).where(
            AccessReviewItem.review_id == campaign.id
        )
    ).scalar_one_or_none()

    assert item is not None
    assert item.user_id == "3f2b8c1e-5d4a-4e6f-9a7b-1c2d3e4f5a6b"
    assert item.role_id == "finance-role-id"
    assert item.role_name == "finance-data-viewer"

    event = db.session.execute(
        db.select(AuditEvent).where(
            AuditEvent.action == "access_review.populate",
            AuditEvent.target_id == str(campaign.id),
        )
    ).scalar_one_or_none()

    assert event is not None
    assert event.actor_user_id == "test-subject"
    assert event.outcome == "success"
    assert event.details["items_added"] == 1


def test_manager_cannot_populate_another_managers_review(client, monkeypatch):
    """
    Verify that a manager cannot populate another manager's campaign.
    """
    _login_user(client, [ACCESS_REVIEW_MANAGER])

    campaign = access_review_service.create_access_review(
        "test campaign",
        "other-manager",
        "user-456",
    )

    db.session.add(
        ManagedRole(
            client_name="employee-portal",
            role_name="finance-data-viewer",
            enabled=True,
        )
    )
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

    response = client.post(
        f"/access-reviews/manage/{campaign.id}/populate",
        data={"user_id": "user-123"},
    )

    assert response.status_code == 404

    item = db.session.execute(
        db.select(AccessReviewItem).where(
            AccessReviewItem.review_id == campaign.id
        )
    ).scalar_one_or_none()

    assert item is None

    event = db.session.execute(
        db.select(AuditEvent).where(
            AuditEvent.action == "access_review.populate",
            AuditEvent.target_id == str(campaign.id),
        )
    ).scalar_one_or_none()

    assert event is None

    fake_get_user.assert_not_called()
    fake_get_roles.assert_not_called()


def test_populate_access_review_requires_manager_role(client, monkeypatch):
    """
    Verify that a reviewer without manager access cannot populate a campaign.
    """
    _login_user(client, [ACCESS_REVIEWER])

    campaign = access_review_service.create_access_review(
        "test campaign",
        "test-subject",
        "user-456",
    )

    fake_populate = Mock()

    monkeypatch.setattr(
        governance_routes,
        "populate_access_review_with_audit",
        fake_populate,
    )

    response = client.post(
        f"/access-reviews/manage/{campaign.id}/populate",
        data={"user_id": "user-123"},
    )

    assert response.status_code == 403
    fake_populate.assert_not_called()


def test_populate_access_review_returns_409_for_non_draft_campaign(
    client,
    monkeypatch,
):
    """
    Verify that population of a non-draft campaign returns HTTP 409.
    """
    _login_user(client, [ACCESS_REVIEW_MANAGER])

    campaign = access_review_service.create_access_review(
        "test campaign",
        "test-subject",
        "reviewer-456",
    )
    campaign.status = "cancelled"
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

    response = client.post(
        f"/access-reviews/manage/{campaign.id}/populate",
        data={"user_id": "user-123"},
    )

    assert response.status_code == 409
    fake_get_user.assert_not_called()
    fake_get_roles.assert_not_called()


def test_populate_access_review_returns_503_on_keycloak_failure(
    client,
    monkeypatch,
):
    """
    Verify that a Keycloak failure returns HTTP 503 without saving snapshots.
    """
    _login_user(client, [ACCESS_REVIEW_MANAGER])

    campaign = access_review_service.create_access_review(
        "Test campaign",
        "test-subject",
        "test-reviewer",
    )

    fake_get_user = Mock(side_effect=KeycloakAdminAPIError("User retrieval failed"))
    fake_resolve_roles = Mock()

    monkeypatch.setattr(
        access_review_service,
        "get_user",
        fake_get_user,
    )

    monkeypatch.setattr(
        access_review_service,
        "resolve_user_client_role_sources",
        fake_resolve_roles,
    )

    response = client.post(
        f"/access-reviews/manage/{campaign.id}/populate",
        data={"user_id": "3f2b8c1e-5d4a-4e6f-9a7b-1c2d3e4f5a6b"},
    )

    assert response.status_code == 503
    saved_items = db.session.execute(
        db.select(AccessReviewItem).where(
            AccessReviewItem.review_id == campaign.id
        )
    ).scalars().all()

    assert saved_items == []
    fake_resolve_roles.assert_not_called()


def test_populate_access_review_returns_400_for_aliased_user_id(client, monkeypatch):
    """
    Verify that an aliased identity ID returns HTTP 400 without contacting Keycloak.
    """
    _login_user(client, [ACCESS_REVIEW_MANAGER])

    campaign = access_review_service.create_access_review(
        "Test campaign",
        "test-subject",
        "test-reviewer",
    )

    fake_get_user = Mock()

    monkeypatch.setattr(
        access_review_service,
        "get_user",
        fake_get_user,
    )

    response = client.post(
        f"/access-reviews/manage/{campaign.id}/populate",
        data={"user_id": "./3f2b8c1e-5d4a-4e6f-9a7b-1c2d3e4f5a6b"},
    )

    assert response.status_code == 400
    fake_get_user.assert_not_called()
    assert db.session.execute(db.select(AccessReviewItem)).scalars().all() == []


@pytest.mark.parametrize(
    "error_type",
    [AuditPersistenceError, SQLAlchemyError],
)
def test_populate_access_review_returns_503_on_persistence_failure(
    client,
    monkeypatch,
    error_type,
):
    """
    Verify that audit or database failures during population return HTTP 503.
    """
    _login_user(client, [ACCESS_REVIEW_MANAGER])

    fake_route = Mock(side_effect=error_type("population_persistence_failed"))

    monkeypatch.setattr(
        governance_routes,
        "populate_access_review_with_audit",
        fake_route,
    )

    response = client.post(
        f"/access-reviews/manage/123/populate",
        data={"user_id": "user-123"},
    )

    assert response.status_code == 503
    fake_route.assert_called_once()


@pytest.mark.parametrize(
    "token_failure",
    ["unreachable", "non_json"],
)
def test_populate_access_review_returns_503_on_service_token_failure(
    client,
    monkeypatch,
    token_failure,
):
    """
    Verify that a failed service-account token request returns HTTP 503.
    """
    _login_user(client, [ACCESS_REVIEW_MANAGER])

    campaign = access_review_service.create_access_review(
        "Test campaign",
        "test-subject",
        "test-reviewer",
    )

    fake_response = Mock()
    fake_response.raise_for_status.return_value = None
    fake_response.json.side_effect = ValueError("not json")

    if token_failure == "unreachable":
        fake_post = Mock(side_effect=requests.ConnectionError("unavailable"))
    else:
        fake_post = Mock(return_value=fake_response)

    monkeypatch.setattr(keycloak_auth_service.requests, "post", fake_post)

    response = client.post(
        f"/access-reviews/manage/{campaign.id}/populate",
        data={"user_id": "3f2b8c1e-5d4a-4e6f-9a7b-1c2d3e4f5a6b"},
    )

    assert response.status_code == 503
    fake_post.assert_called_once()
    assert db.session.execute(db.select(AccessReviewItem)).scalars().all() == []
