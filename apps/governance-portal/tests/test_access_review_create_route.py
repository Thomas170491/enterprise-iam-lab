import json
from unittest.mock import Mock

import pytest
from sqlalchemy.exc import SQLAlchemyError

from auth.permissions import ACCESS_REVIEW_MANAGER
from extensions import db
from models import AccessReview
from services.exceptions import AuditPersistenceError, KeycloakAdminAPIError
from tests.access_review_helpers import _login_user

import governance.routes as governance_routes
import services.access_review_service as access_review_service


def test_access_review_manager_can_create_campaign(client, monkeypatch):
    """
    Verify that an access review manager can create a draft campaign.
    """
    _login_user(client, [ACCESS_REVIEW_MANAGER])

    monkeypatch.setattr(
        access_review_service,
        "validate_access_review_reviewer",
        lambda **kwargs: {
            "id": "9a1d4c7e-2b3f-4e58-8c6a-0d1e2f3a4b5c",
            "username": "reviewer",
            "enabled": True,
        },
    )

    response = client.post(
        "/access-reviews/new",
        data={
            "name": "September access review",
            "reviewer_user_id": "9a1d4c7e-2b3f-4e58-8c6a-0d1e2f3a4b5c",
            "due_at": "",
        },
    )

    assert response.status_code == 303

    review = db.session.execute(
        db.select(AccessReview).where(
            AccessReview.name == "September access review"
        )
    ).scalar_one()

    assert review.created_by_user_id == "test-subject"
    assert review.reviewer_user_id == "9a1d4c7e-2b3f-4e58-8c6a-0d1e2f3a4b5c"
    assert review.status == "draft"
    assert review.due_at is None

    assert response.headers["Location"].endswith(
        f"/access-reviews/manage/{review.id}"
    )


def test_create_access_review_rejects_ineligible_reviewer(client, monkeypatch):
    """
    Verify that an ineligible reviewer causes HTTP 400 without saving a campaign.
    """
    _login_user(client, [ACCESS_REVIEW_MANAGER])

    fake_validate = Mock(side_effect=ValueError("reviewer_missing_required_role"))

    monkeypatch.setattr(
        access_review_service,
        "validate_access_review_reviewer",
        fake_validate,
    )

    response = client.post(
        "/access-reviews/new",
        data={
            "name": "September access review",
            "reviewer_user_id": "4e7b2a9c-1d3f-4c8e-b5a6-7f0e1d2c3b4a",
            "due_at": "",
        },
    )

    assert response.status_code == 400
    assert db.session.execute(
        db.select(AccessReview)
    ).scalars().all() == []

    fake_validate.assert_called_once()


def test_create_access_review_logs_non_uuid_reviewer_denial(
    client, monkeypatch, caplog
):
    """
    Verify that a non-UUID reviewer ID answers 400 and logs one denial without the submitted text.
    """
    _login_user(client, [ACCESS_REVIEW_MANAGER])

    fake_get_user = Mock()
    fake_get_roles = Mock()
    monkeypatch.setattr(access_review_service, "get_user", fake_get_user)
    monkeypatch.setattr(
        access_review_service, "get_effective_client_roles", fake_get_roles
    )

    bad_id = "../3f2b8c1e-5d4a-4e6f-9a7b-1c2d3e4f5a6b"

    with caplog.at_level("WARNING"):
        response = client.post(
            "/access-reviews/new",
            data={
                "name": "September access review",
                "reviewer_user_id": bad_id,
                "due_at": "",
            },
        )

    assert response.status_code == 400
    fake_get_user.assert_not_called()
    fake_get_roles.assert_not_called()
    assert db.session.execute(db.select(AccessReview)).scalars().all() == []

    events = [
        json.loads(record.getMessage())
        for record in caplog.records
        if record.getMessage().startswith("{")
    ]

    assert len(events) == 1
    assert events[0]["event"] == "access_review.create"
    assert events[0]["outcome"] == "denied"
    assert events[0]["reason"] == "invalid_reviewer_user_id"
    assert bad_id not in caplog.text


def test_create_access_review_returns_503_when_reviewer_verification_fails(
    client,
    monkeypatch,
):
    """
    Verify that a Keycloak verification failure returns HTTP 503 without saving a campaign.
    """
    _login_user(client, [ACCESS_REVIEW_MANAGER])

    fake_validate = Mock(side_effect=KeycloakAdminAPIError("User retrival failed"))

    monkeypatch.setattr(
        access_review_service,
        "validate_access_review_reviewer",
        fake_validate,
    )

    response = client.post(
        "/access-reviews/new",
        data={
            "name": "September access review",
            "reviewer_user_id": "4e7b2a9c-1d3f-4c8e-b5a6-7f0e1d2c3b4a",
            "due_at": "",
        },
    )

    html = response.get_data(as_text=True)

    assert response.status_code == 503
    assert db.session.execute(
        db.select(AccessReview)
    ).scalars().all() == []
    assert "The reviewer could not be verified. Please try again." in html

    fake_validate.assert_called_once()


@pytest.mark.parametrize(
    "error_type",
    [AuditPersistenceError, SQLAlchemyError],
)
def test_create_access_review_returns_503_on_persistence_failure(
    client,
    monkeypatch,
    error_type,
):
    """
    Verify that audit or database failures during campaign creation return HTTP 503.
    """
    _login_user(client, [ACCESS_REVIEW_MANAGER])

    fake_create = Mock(side_effect=error_type("campaign_persistence_failed"))

    monkeypatch.setattr(
        governance_routes,
        "create_access_review_with_audit",
        fake_create,
    )

    response = client.post(
        "/access-reviews/new",
        data={
            "name": "September access review",
            "reviewer_user_id": "4e7b2a9c-1d3f-4c8e-b5a6-7f0e1d2c3b4a",
            "due_at": "",
        },
    )

    html = response.get_data(as_text=True)

    assert response.status_code == 503
    assert "The campaign could not be saved. Please try again." in html
    fake_create.assert_called_once()
    
def test_create_access_review_explains_and_logs_self_assigned_reviewer(
    client, monkeypatch, caplog
):
    """
    Verify that naming yourself as reviewer answers 400 with an explanation and logs one denial.
    """
    _login_user(client, [ACCESS_REVIEW_MANAGER])

    monkeypatch.setattr(
        governance_routes,
        "create_access_review_with_audit",
        Mock(side_effect=ValueError("access_review_creator_cannot_be_reviewer")),
    )

    with caplog.at_level("WARNING"):
        response = client.post(
            "/access-reviews/new",
            data={
                "name": "September access review",
                "reviewer_user_id": "3f2b8c1e-5d4a-4e6f-9a7b-1c2d3e4f5a6b",
                "due_at": "",
            },
        )

    assert response.status_code == 400
    assert "You cannot review a campaign you created" in response.get_data(as_text=True)

    events = [
        json.loads(record.getMessage())
        for record in caplog.records
        if record.getMessage().startswith("{")
    ]

    assert len(events) == 1
    assert events[0]["event"] == "access_review.create"
    assert events[0]["outcome"] == "denied"
    assert events[0]["reason"] == "access_review_creator_cannot_be_reviewer"


def test_create_access_review_keeps_generic_message_for_other_reasons(client, monkeypatch):
    """
    Verify that a reason other than the creator rule shows the generic message, not the creator one.
    """
    _login_user(client, [ACCESS_REVIEW_MANAGER])

    monkeypatch.setattr(
        governance_routes,
        "create_access_review_with_audit",
        Mock(side_effect=ValueError("reviewer_not_enabled")),
    )

    response = client.post(
        "/access-reviews/new",
        data={
            "name": "September access review",
            "reviewer_user_id": "3f2b8c1e-5d4a-4e6f-9a7b-1c2d3e4f5a6b",
            "due_at": "",
        },
    )

    html = response.get_data(as_text=True)

    assert response.status_code == 400
    assert "Enter a campaign name and a valid reviewer ID." in html
    assert "You cannot review a campaign you created" not in html


def test_create_access_review_refuses_creator_through_the_real_service(
    client, monkeypatch, caplog
):
    """
    Verify end to end that a manager whose own id Keycloak returns for the reviewer is refused.
    """
    manager_id = "9a1d4c7e-2b3f-4e58-8c6a-0d1e2f3a4b5c"
    _login_user(client, [ACCESS_REVIEW_MANAGER], sub=manager_id)

    monkeypatch.setattr(
        access_review_service,
        "validate_access_review_reviewer",
        lambda **kwargs: {"id": manager_id, "enabled": True},
    )

    with caplog.at_level("WARNING"):
        response = client.post(
            "/access-reviews/new",
            data={
                "name": "September access review",
                "reviewer_user_id": manager_id,
                "due_at": "",
            },
        )

    assert response.status_code == 400
    assert "You cannot review a campaign you created" in response.get_data(as_text=True)
    assert db.session.execute(db.select(AccessReview)).scalars().all() == []

    events = [
        json.loads(record.getMessage())
        for record in caplog.records
        if record.getMessage().startswith("{")
    ]

    assert len(events) == 1
    assert events[0]["outcome"] == "denied"
    assert events[0]["reason"] == "access_review_creator_cannot_be_reviewer"
