from unittest.mock import Mock

import pytest
from sqlalchemy.exc import SQLAlchemyError

from auth.permissions import ACCESS_REVIEW_MANAGER, ACCESS_REVIEWER
from extensions import db
from models import AccessReview, AccessReviewItem, AuditEvent
from services.exceptions import AuditPersistenceError
from tests.access_review_helpers import _login_user

import governance.routes as governance_routes
import services.access_review_service as access_review_service


def test_manager_can_open_own_access_review(client):
    """
    Verify that a manager can open their campaign and receives the correct redirect.
    """
    _login_user(client,[ACCESS_REVIEW_MANAGER])

    campaign = access_review_service.create_access_review("Test campaign", "test-subject", "reviewer-123")

    access_review_service.add_access_review_item(
    review_id=campaign.id,
    user_id="user-123",
    username="alice",
    client_name="employee-portal",
    role_id="finance-role-id",
    role_name="finance-data-viewer",
)

    db.session.commit()

    response = client.post(
        f"/access-reviews/manage/{campaign.id}/open"
    )

    assert response.status_code == 303
    assert response.headers["Location"] == f"/access-reviews/manage/{campaign.id}"

    saved_review = db.session.get(AccessReview, campaign.id)

    assert saved_review is not None
    assert saved_review.status == "open"

    event = db.session.execute(
        db.select(AuditEvent).where(
            AuditEvent.action == "access_review.open",
            AuditEvent.target_id == str(campaign.id)
        )
    ).scalar_one_or_none()

    assert event is not None
    assert event.actor_user_id == "test-subject"
    assert event.outcome == "success"
    assert event.details["previous_status"] == "draft"
    assert event.details["new_status"] == "open"


def test_open_access_review_returns_409_for_empty_campaign(client):
    """
    Verify that opening an empty campaign returns HTTP 409 and leaves it in draft.
    """
    _login_user(client, [ACCESS_REVIEW_MANAGER])

    campaign = access_review_service.create_access_review(
        "Empty campaign",
        "test-subject",
        "reviewer-123",
    )
    db.session.commit()

    response = client.post(
        f"/access-reviews/manage/{campaign.id}/open"
    )

    assert response.status_code == 409

    saved_review = db.session.get(AccessReview, campaign.id)
    event = db.session.execute(
        db.select(AuditEvent).where(
            AuditEvent.action == "access_review.open",
            AuditEvent.target_id == str(campaign.id),
        )
    ).scalar_one_or_none()

    assert saved_review is not None
    assert saved_review.status == "draft"
    assert event is None


def test_manager_cannot_open_another_managers_review(client):
    """
    Verify that opening another manager's campaign returns HTTP 404 without changing its status.
    """
    _login_user(client, [ACCESS_REVIEW_MANAGER])

    campaign = access_review_service.create_access_review(
        "Other manager campaign",
        "other-manager",
        "reviewer-123",
    )
    access_review_service.add_access_review_item(
        review_id=campaign.id,
        user_id="user-123",
        username="alice",
        client_name="employee-portal",
        role_id="finance-role-id",
        role_name="finance-data-viewer",
    )
    db.session.commit()

    response = client.post(
        f"/access-reviews/manage/{campaign.id}/open"
    )

    assert response.status_code == 404

    saved_review = db.session.get(AccessReview, campaign.id)
    event = db.session.execute(
        db.select(AuditEvent).where(
            AuditEvent.action == "access_review.open",
            AuditEvent.target_id == str(campaign.id),
        )
    ).scalar_one_or_none()

    assert saved_review is not None
    assert saved_review.status == "draft"
    assert event is None


def test_open_access_review_requires_manager_role(client, monkeypatch):
    """
    Verify that a reviewer without manager access cannot trigger campaign opening.
    """
    _login_user(client, [ACCESS_REVIEWER])

    fake_open = Mock()
    monkeypatch.setattr(
        governance_routes,
        "open_access_review_with_audit",
        fake_open,
    )

    response = client.post("/access-reviews/manage/123/open")

    assert response.status_code == 403
    fake_open.assert_not_called()


@pytest.mark.parametrize(
    "error_type",
    [AuditPersistenceError, SQLAlchemyError],
)
def test_open_access_review_returns_503_on_persistence_failure(
    client,
    monkeypatch,
    error_type,
):
    """
    Verify that audit or database failures during campaign opening return HTTP 503.
    """
    _login_user(client, [ACCESS_REVIEW_MANAGER])

    fake_open = Mock(side_effect=error_type("opening_persistence_failed"))
    monkeypatch.setattr(
        governance_routes,
        "open_access_review_with_audit",
        fake_open,
    )

    response = client.post("/access-reviews/manage/123/open")

    assert response.status_code == 503


@pytest.mark.parametrize("status", ["draft", "open"])
def test_manager_can_cancel_own_access_review(client, status):
    """
    Verify that cancellation commits the status and audit event while preserving snapshots.
    """
    _login_user(client, [ACCESS_REVIEW_MANAGER])
    campaign = access_review_service.create_access_review(
        "Campaign to cancel", "test-subject", "reviewer-123"
    )
    item = access_review_service.add_access_review_item(
        review_id=campaign.id,
        user_id="user-123",
        username="alice",
        client_name="employee-portal",
        role_id="finance-role-id",
        role_name="finance-data-viewer",
    )
    campaign.status = status
    db.session.commit()
    campaign_id, item_id = campaign.id, item.id

    response = client.post(f"/access-reviews/manage/{campaign_id}/cancel")

    assert response.status_code == 303
    assert response.headers["Location"] == f"/access-reviews/manage/{campaign_id}"
    db.session.rollback()

    saved_review = db.session.get(AccessReview, campaign_id)
    saved_item = db.session.get(AccessReviewItem, item_id)
    event = db.session.execute(
        db.select(AuditEvent).where(
            AuditEvent.action == "access_review.cancel",
            AuditEvent.target_id == str(campaign_id),
        )
    ).scalar_one_or_none()

    assert saved_review is not None
    assert saved_review.status == "cancelled"
    assert saved_item is not None
    assert saved_item.review_id == campaign_id
    assert event is not None
    assert event.actor_user_id == "test-subject"
    assert event.actor_username == "test-user"
    assert event.target_type == "access_review"
    assert event.target_name == "Campaign to cancel"
    assert event.outcome == "success"
    assert event.details["source"] == "governance-portal"
    assert event.details["reviewer_user_id"] == "reviewer-123"
    assert event.details["previous_status"] == status
    assert event.details["new_status"] == "cancelled"
    assert event.details["item_count"] == 1


def test_manager_cannot_cancel_another_managers_review(client):
    """
    Verify that another manager's campaign and snapshots remain unchanged after denial.
    """
    _login_user(client, [ACCESS_REVIEW_MANAGER])
    campaign = access_review_service.create_access_review(
        "Other manager campaign", "other-manager", "reviewer-123"
    )
    item = access_review_service.add_access_review_item(
        review_id=campaign.id,
        user_id="user-123",
        username="alice",
        client_name="employee-portal",
        role_id="finance-role-id",
        role_name="finance-data-viewer",
    )
    db.session.commit()
    campaign_id, item_id = campaign.id, item.id

    response = client.post(f"/access-reviews/manage/{campaign_id}/cancel")

    assert response.status_code == 404
    saved_review = db.session.get(AccessReview, campaign_id)
    assert saved_review is not None
    assert saved_review.status == "draft"
    assert db.session.get(AccessReviewItem, item_id) is not None
    event = db.session.execute(
        db.select(AuditEvent).where(
            AuditEvent.action == "access_review.cancel",
            AuditEvent.target_id == str(campaign_id),
        )
    ).scalar_one_or_none()
    assert event is None


@pytest.mark.parametrize("client_roles", [[], [ACCESS_REVIEWER]])
def test_cancel_access_review_requires_manager_role(client, monkeypatch, client_roles):
    """
    Verify that users without manager access cannot invoke campaign cancellation.
    """
    _login_user(client, client_roles)
    fake_cancel = Mock()
    monkeypatch.setattr(
        governance_routes, "cancel_access_review_with_audit", fake_cancel
    )

    response = client.post("/access-reviews/manage/123/cancel")

    assert response.status_code == 403
    fake_cancel.assert_not_called()


@pytest.mark.parametrize("status", ["completed", "cancelled"])
def test_cancel_access_review_returns_409_for_invalid_status(client, status):
    """
    Verify that terminal campaigns reject cancellation without changing snapshots or status.
    """
    _login_user(client, [ACCESS_REVIEW_MANAGER])
    campaign = access_review_service.create_access_review(
        "Terminal campaign", "test-subject", "reviewer-123"
    )
    item = access_review_service.add_access_review_item(
        review_id=campaign.id,
        user_id="user-123",
        username="alice",
        client_name="employee-portal",
        role_id="finance-role-id",
        role_name="finance-data-viewer",
    )
    campaign.status = status
    db.session.commit()
    campaign_id, item_id = campaign.id, item.id

    response = client.post(f"/access-reviews/manage/{campaign_id}/cancel")

    assert response.status_code == 409
    saved_review = db.session.get(AccessReview, campaign_id)
    assert saved_review is not None
    assert saved_review.status == status
    assert db.session.get(AccessReviewItem, item_id) is not None
    event = db.session.execute(
        db.select(AuditEvent).where(
            AuditEvent.action == "access_review.cancel",
            AuditEvent.target_id == str(campaign_id),
        )
    ).scalar_one_or_none()
    assert event is None


@pytest.mark.parametrize("error_type", [AuditPersistenceError, SQLAlchemyError])
def test_cancel_access_review_returns_503_on_persistence_failure(
    client, monkeypatch, error_type
):
    """
    Verify that audit or database failures during cancellation return HTTP 503.
    """
    _login_user(client, [ACCESS_REVIEW_MANAGER])
    fake_cancel = Mock(side_effect=error_type("cancellation_persistence_failed"))
    monkeypatch.setattr(
        governance_routes, "cancel_access_review_with_audit", fake_cancel
    )

    response = client.post("/access-reviews/manage/123/cancel")

    assert response.status_code == 503
    fake_cancel.assert_called_once_with(
        review_id=123,
        manager_user_id="test-subject",
        actor_username="test-user",
    )
