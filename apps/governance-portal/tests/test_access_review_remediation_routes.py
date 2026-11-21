import json
from urllib.parse import urlsplit
from unittest.mock import ANY, Mock

import pytest
from flask import url_for
from sqlalchemy.exc import SQLAlchemyError

from auth.permissions import ACCESS_REVIEW_MANAGER, ACCESS_REVIEWER
from extensions import db
from services.exceptions import (
    AuditPersistenceError,
    KeycloakAdminAPIError,
    RoleAdministrationPolicyError,
)
from tests.access_review_helpers import _CSRFFormParser, _login_user

import governance.routes as governance_routes
import services.access_review_service as access_review_service

REVIEWER_ID = "7a1d2c3b-4e5f-4a6b-8c7d-9e0f1a2b3c4d"


def _manager_campaign_with_decided_item(decision="revoke"):
    """
    Create an open campaign owned by the signed-in manager with one item decided by another reviewer.
    """
    campaign = access_review_service.create_access_review(
        name="Remediation campaign",
        created_by_user_id="test-subject",
        reviewer_user_id=REVIEWER_ID,
    )
    item = access_review_service.add_access_review_item(
        review_id=campaign.id,
        user_id="user-123",
        username="alice",
        client_name="employee-portal",
        role_id="finance-role-id",
        role_name="finance-data-viewer",
    )
    access_review_service.open_access_review(campaign.id)
    db.session.commit()
    review_id, item_id = campaign.id, item.id

    access_review_service.record_access_review_decision_with_audit(
        review_id=review_id,
        item_id=item_id,
        reviewer_user_id=REVIEWER_ID,
        actor_username="reviewer",
        decision=decision,
    )
    return review_id, item_id


def _remediate_url(review_id, item_id):
    """
    Return the remediation route for an item.
    """
    return f"/access-reviews/manage/{review_id}/items/{item_id}/remediate"


def _logged_events(caplog):
    """
    Return the structured governance events captured in the log.
    """
    return [
        json.loads(record.getMessage())
        for record in caplog.records
        if record.getMessage().startswith("{")
    ]


def test_manager_can_remediate_revoked_item(client, monkeypatch):
    """
    Verify that the campaign manager's remediation request runs the service and redirects to the campaign.
    """
    _login_user(client, [ACCESS_REVIEW_MANAGER])
    review_id, item_id = _manager_campaign_with_decided_item()
    fake_service = Mock()
    monkeypatch.setattr(
        governance_routes, "remediate_access_review_item_with_audit", fake_service
    )

    response = client.post(_remediate_url(review_id, item_id))

    assert response.status_code == 303
    assert response.headers["Location"] == f"/access-reviews/manage/{review_id}"
    fake_service.assert_called_once_with(
        review_id=review_id,
        item_id=item_id,
        manager_user_id="test-subject",
        actor_username="test-user",
        admin_api_url=ANY,
        token_url=ANY,
        client_id="iam-governance-service",
        client_secret=ANY,
    )


def test_remediation_requires_manager_role(client, monkeypatch):
    """
    Verify that a reviewer cannot remediate and the service is never called.
    """
    _login_user(client, [ACCESS_REVIEWER])
    review_id, item_id = _manager_campaign_with_decided_item()
    fake_service = Mock()
    monkeypatch.setattr(
        governance_routes, "remediate_access_review_item_with_audit", fake_service
    )

    response = client.post(_remediate_url(review_id, item_id))

    assert response.status_code == 403
    fake_service.assert_not_called()


def test_remediation_redirects_anonymous_user_to_login(client, monkeypatch):
    """
    Verify that an anonymous remediation request is sent to login and the service is never called.
    """
    review_id, item_id = _manager_campaign_with_decided_item()
    fake_service = Mock()
    monkeypatch.setattr(
        governance_routes, "remediate_access_review_item_with_audit", fake_service
    )

    response = client.post(_remediate_url(review_id, item_id))

    assert response.status_code == 302

    with client.application.test_request_context():
        login_url = url_for("auth.login")

    assert urlsplit(response.headers["Location"]).path == login_url
    fake_service.assert_not_called()


@pytest.mark.parametrize(
    "error, expected_status, expected_outcome, expected_reason",
    [
        (ValueError("access_review_not_found"), 404, "denied", "access_review_not_found"),
        (ValueError("access_review_item_not_found"), 404, "denied", "access_review_item_not_found"),
        (ValueError("access_review_not_open"), 409, "denied", "access_review_not_open"),
        (
            ValueError("access_review_item_not_pending_remediation"),
            409,
            "denied",
            "access_review_item_not_pending_remediation",
        ),
        (ValueError("role_source_untraceable"), 409, "denied", "role_source_untraceable"),
        (RoleAdministrationPolicyError("role_id_mismatch"), 409, "denied", "role_id_mismatch"),
        (RoleAdministrationPolicyError("unmanaged_role"), 409, "denied", "unmanaged_role"),
        (RoleAdministrationPolicyError("unmanaged_client"), 409, "denied", "unmanaged_client"),
        (RoleAdministrationPolicyError("invalid_user_id"), 409, "denied", "invalid_user_id"),
        (KeycloakAdminAPIError("Keycloak unavailable"), 503, "failure", "remediation_keycloak_failed"),
        (AuditPersistenceError("audit unavailable"), 503, "failure", "remediation_persistence_failed"),
        (SQLAlchemyError("database unavailable"), 503, "failure", "remediation_persistence_failed"),
    ],
    ids=[
        "campaign_not_found",
        "item_not_found",
        "campaign_not_open",
        "not_pending",
        "untraceable",
        "role_id_mismatch",
        "unmanaged_role",
        "unmanaged_client",
        "invalid_user_id",
        "keycloak_failure",
        "audit_failure",
        "database_failure",
    ],
)
def test_remediation_maps_failures_and_logs_them(
    client, monkeypatch, caplog, error, expected_status, expected_outcome, expected_reason
):
    """
    Verify that each remediation failure answers its status and logs one event with a stable reason and no exception text.
    """
    _login_user(client, [ACCESS_REVIEW_MANAGER])
    review_id, item_id = _manager_campaign_with_decided_item()
    monkeypatch.setattr(
        governance_routes,
        "remediate_access_review_item_with_audit",
        Mock(side_effect=error),
    )

    with caplog.at_level("WARNING"):
        response = client.post(_remediate_url(review_id, item_id))

    assert response.status_code == expected_status

    events = _logged_events(caplog)
    assert len(events) == 1
    assert events[0]["event"] == "access_review.remediation"
    assert events[0]["outcome"] == expected_outcome
    assert events[0]["reason"] == expected_reason
    assert events[0]["target_id"] == str(item_id)
    assert events[0]["review_id"] == str(review_id)
    assert "unavailable" not in caplog.text


def test_remediation_returns_400_for_unmapped_error_without_logging_it(
    client, monkeypatch, caplog
):
    """
    Verify that an unknown service error answers 400 and its message is never logged.
    """
    _login_user(client, [ACCESS_REVIEW_MANAGER])
    review_id, item_id = _manager_campaign_with_decided_item()
    monkeypatch.setattr(
        governance_routes,
        "remediate_access_review_item_with_audit",
        Mock(side_effect=ValueError("something unexpected")),
    )

    with caplog.at_level("WARNING"):
        response = client.post(_remediate_url(review_id, item_id))

    assert response.status_code == 400
    assert _logged_events(caplog) == []
    assert "something unexpected" not in caplog.text


def test_manager_view_offers_remediation_for_pending_revoked_item(client):
    """
    Verify that the manager's campaign page offers a remediation form for a revoked item pending remediation.
    """
    _login_user(client, [ACCESS_REVIEW_MANAGER])
    review_id, item_id = _manager_campaign_with_decided_item()

    html = client.get(f"/access-reviews/manage/{review_id}").get_data(as_text=True)

    assert _remediate_url(review_id, item_id) in html
    assert "Remediate" in html


def test_manager_view_hides_remediation_for_retained_item(client):
    """
    Verify that a retained item offers no remediation form.
    """
    _login_user(client, [ACCESS_REVIEW_MANAGER])
    review_id, item_id = _manager_campaign_with_decided_item(decision="retain")

    response = client.get(f"/access-reviews/manage/{review_id}")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "alice" in html
    assert _remediate_url(review_id, item_id) not in html


def test_manager_view_hides_remediation_once_item_is_remediated(client):
    """
    Verify that an item whose remediation finished offers no remediation form.
    """
    _login_user(client, [ACCESS_REVIEW_MANAGER])
    review_id, item_id = _manager_campaign_with_decided_item()
    db.session.execute(
        db.update(access_review_service.AccessReviewItem)
        .where(access_review_service.AccessReviewItem.id == item_id)
        .values(remediation_status="completed")
    )
    db.session.commit()

    response = client.get(f"/access-reviews/manage/{review_id}")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "alice" in html
    assert _remediate_url(review_id, item_id) not in html
    assert "Remediation: Completed" in html


def test_manager_view_hides_remediation_for_cancelled_campaign(client):
    """
    Verify that a cancelled campaign offers no remediation form.
    """
    _login_user(client, [ACCESS_REVIEW_MANAGER])
    review_id, item_id = _manager_campaign_with_decided_item()
    access_review_service.cancel_access_review(review_id)
    db.session.commit()

    response = client.get(f"/access-reviews/manage/{review_id}")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "alice" in html
    assert _remediate_url(review_id, item_id) not in html


def test_reviewer_view_never_offers_remediation(client):
    """
    Verify that the reviewer's campaign page has no remediation form.
    """
    review_id, item_id = _manager_campaign_with_decided_item()
    _login_user(client, [ACCESS_REVIEWER], sub=REVIEWER_ID)

    response = client.get(f"/access-reviews/{review_id}")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "alice" in html
    assert _remediate_url(review_id, item_id) not in html


@pytest.mark.parametrize("token_state", ["missing", "invalid", "valid"])
def test_remediation_requires_valid_csrf_token(client, monkeypatch, token_state):
    """
    Verify that the remediation route rejects missing or invalid CSRF tokens and accepts the form's token.
    """
    monkeypatch.setitem(client.application.config, "WTF_CSRF_ENABLED", True)
    _login_user(client, [ACCESS_REVIEW_MANAGER])
    review_id, item_id = _manager_campaign_with_decided_item()
    fake_service = Mock()
    monkeypatch.setattr(
        governance_routes, "remediate_access_review_item_with_audit", fake_service
    )
    post_url = _remediate_url(review_id, item_id)

    form_response = client.get(f"/access-reviews/manage/{review_id}")
    parser = _CSRFFormParser(post_url)
    parser.feed(form_response.get_data(as_text=True))
    assert parser.csrf_token, f"Missing CSRF token in form for {post_url}"

    data = {}
    if token_state == "valid":
        data["csrf_token"] = parser.csrf_token
    elif token_state == "invalid":
        data["csrf_token"] = "invalid-test-token"

    response = client.post(post_url, data=data)

    if token_state == "valid":
        assert response.status_code == 303
        fake_service.assert_called_once()
    else:
        assert response.status_code == 400
        fake_service.assert_not_called()
