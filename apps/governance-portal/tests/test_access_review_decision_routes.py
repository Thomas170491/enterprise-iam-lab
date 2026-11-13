import json
from unittest.mock import Mock

import pytest

from auth.permissions import ACCESS_REVIEWER
from extensions import db
from models import AccessReviewItem, AuditEvent
from services.exceptions import AuditPersistenceError
from tests.access_review_helpers import _login_user

import governance.routes as governance_routes
import services.access_review_service as access_review_service


def test_record_access_review_decision_allows_assigned_reviewer_to_retain(client):
    """
    Verify that the assigned reviewer can retain an item in an open campaign.
    """
    _login_user(client, [ACCESS_REVIEWER])

    campaign = access_review_service.create_access_review(
        name="Decision campaign",
        created_by_user_id="manager-123",
        reviewer_user_id="test-subject",
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
    campaign_id, item_id = campaign.id, item.id
    db.session.commit()

    response = client.post(
        f"/access-reviews/{campaign_id}/items/{item_id}/decision",
        data={"decision": "retain"},
    )

    assert response.status_code == 303
    assert response.headers["Location"] == f"/access-reviews/{campaign_id}"

    db.session.expire_all()
    saved_item = db.session.get(AccessReviewItem, item_id)
    assert saved_item is not None
    assert saved_item.decision == "retain"
    assert saved_item.decided_by_user_id == "test-subject"
    assert saved_item.decided_at is not None

    event = db.session.execute(
        db.select(AuditEvent).where(
            AuditEvent.action == "access_review.decision",
            AuditEvent.target_id == str(item_id),
        )
    ).scalar_one_or_none()

    assert event is not None
    assert event.actor_user_id == "test-subject"
    assert event.details["review_id"] == campaign_id
    assert event.details["decision"] == "retain"


def test_record_access_review_decision_stores_form_comment(client):
    """
    Verify that the reviewer's comment from the decision form is stored with the decision.
    """
    _login_user(client, [ACCESS_REVIEWER])

    campaign = access_review_service.create_access_review(
        name="Decision campaign",
        created_by_user_id="manager-123",
        reviewer_user_id="test-subject",
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
    campaign_id, item_id = campaign.id, item.id
    db.session.commit()

    response = client.post(
        f"/access-reviews/{campaign_id}/items/{item_id}/decision",
        data={"decision": "revoke", "comment": "  moved to Security in October  "},
    )

    assert response.status_code == 303

    db.session.expire_all()
    saved_item = db.session.get(AccessReviewItem, item_id)
    assert saved_item.decision == "revoke"
    assert saved_item.decision_comment == "moved to Security in October"


def test_record_access_review_decision_hides_campaign_from_other_reviewer(client):
    """
    Verify that a reviewer cannot decide an item in another reviewer's campaign.
    """
    _login_user(client, [ACCESS_REVIEWER])

    campaign = access_review_service.create_access_review(
        name="Decision campaign",
        created_by_user_id="manager-123",
        reviewer_user_id="other-reviewer",
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
    campaign_id, item_id = campaign.id, item.id
    db.session.commit()

    response = client.post(
        f"/access-reviews/{campaign_id}/items/{item_id}/decision",
        data={"decision": "retain"},
    )

    assert response.status_code == 404
    db.session.expire_all()
    saved_item = db.session.get(AccessReviewItem, item_id)
    assert saved_item is not None
    assert saved_item.decision is None

    event = db.session.execute(
        db.select(AuditEvent).where(
            AuditEvent.action == "access_review.decision",
            AuditEvent.target_id == str(item_id),
        )
    ).scalar_one_or_none()
    assert event is None


def test_record_access_review_decision_overlong_comment_returns_400(client):
    """
    Verify that an overlong comment from the decision form returns HTTP 400
    and leaves the item unchanged.
    """
    
    _login_user(client, [ACCESS_REVIEWER])

    campaign = access_review_service.create_access_review(
        name="Decision campaign",
        created_by_user_id="manager-123",
        reviewer_user_id="test-subject",
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
    campaign_id, item_id = campaign.id, item.id
    db.session.commit()

    response = client.post(
        f"/access-reviews/{campaign_id}/items/{item_id}/decision",
        data={"decision": "revoke", "comment": "x" * 1001},
    )

    assert response.status_code == 400

    db.session.expire_all()
    saved_item = db.session.get(AccessReviewItem, item_id)
    assert saved_item.decision is None


def test_record_access_review_decision_rejects_self_certification(client):
    """
    Verify that a reviewer cannot decide their own access review item.
    """

    _login_user(client, [ACCESS_REVIEWER])

    campaign = access_review_service.create_access_review(
        name="Decision campaign",
        created_by_user_id="manager-123",
        reviewer_user_id="test-subject",
    )
    item = access_review_service.add_access_review_item(
        review_id=campaign.id,
        user_id="test-subject",
        username="alice",
        client_name="employee-portal",
        role_id="finance-role-id",
        role_name="finance-data-viewer",
    )
    access_review_service.open_access_review(campaign.id)
    campaign_id, item_id = campaign.id, item.id
    db.session.commit()

    response = client.post(
        f"/access-reviews/{campaign_id}/items/{item_id}/decision",
        data={"decision": "retain"},
    )

    assert response.status_code == 403
    db.session.expire_all()
    saved_item = db.session.get(AccessReviewItem, item_id)
    assert saved_item is not None
    assert saved_item.decision is None

    event = db.session.execute(
        db.select(AuditEvent).where(
            AuditEvent.action == "access_review.decision",
            AuditEvent.target_id == str(item_id),
        )
    ).scalar_one_or_none()
    assert event is None


@pytest.mark.parametrize("decision", ["", "approve"])
def test_record_access_review_decision_rejects_invalid_value(client, decision):
    """
    Verify that invalid decisions leave the item unchanged and create no audit event.
    """
    _login_user(client, [ACCESS_REVIEWER])

    campaign = access_review_service.create_access_review(
        name="Decision campaign",
        created_by_user_id="manager-123",
        reviewer_user_id="test-subject",
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
    campaign_id, item_id = campaign.id, item.id
    db.session.commit()

    response = client.post(
        f"/access-reviews/{campaign_id}/items/{item_id}/decision",
        data={"decision": decision},
    )

    assert response.status_code == 400
    db.session.expire_all()
    saved_item = db.session.get(AccessReviewItem, item_id)
    assert saved_item is not None
    assert saved_item.decision is None

    event = db.session.execute(
        db.select(AuditEvent).where(
            AuditEvent.action == "access_review.decision",
            AuditEvent.target_id == str(item_id),
        )
    ).scalar_one_or_none()
    assert event is None


@pytest.mark.parametrize("status", ["draft", "completed", "cancelled"])
def test_record_access_review_decision_rejects_non_open_campaign(client, status):
    """
    Verify that items cannot be decided outside an open campaign.
    """
    _login_user(client, [ACCESS_REVIEWER])

    campaign = access_review_service.create_access_review(
        name="Decision campaign",
        created_by_user_id="manager-123",
        reviewer_user_id="test-subject",
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

    response = client.post(
        f"/access-reviews/{campaign_id}/items/{item_id}/decision",
        data={"decision": "retain"},
    )

    event = db.session.execute(
        db.select(AuditEvent).where(
            AuditEvent.action == "access_review.decision",
            AuditEvent.target_id == str(item_id),
        )
    ).scalar_one_or_none()

    assert response.status_code == 409
    assert item.decision is None
    assert event is None


def test_record_access_review_decision_rejects_item_from_another_campaign(client):
    """
    Verify that a decision URL cannot target an item from another campaign.
    """
    _login_user(client, [ACCESS_REVIEWER])

    campaign = access_review_service.create_access_review(
        name="Decision campaign",
        created_by_user_id="manager-123",
        reviewer_user_id="test-subject",
    )
    access_review_service.add_access_review_item(
        review_id=campaign.id,
        user_id="user-123",
        username="alice",
        client_name="employee-portal",
        role_id="finance-role-id",
        role_name="finance-data-viewer",
    )

    other_campaign = access_review_service.create_access_review(
        name="Other campaign",
        created_by_user_id="manager-456",
        reviewer_user_id="test-subject",
    )
    other_item = access_review_service.add_access_review_item(
        review_id=other_campaign.id,
        user_id="other-subject",
        username="bob",
        client_name="employee-portal",
        role_id="hr-role-id",
        role_name="hr-data-viewer",
    )

    access_review_service.open_access_review(campaign.id)
    access_review_service.open_access_review(other_campaign.id)

    campaign_id = campaign.id
    other_item_id = other_item.id
    db.session.commit()

    response = client.post(
        f"/access-reviews/{campaign_id}/items/{other_item_id}/decision",
        data={"decision": "retain"},
    )

    assert response.status_code == 404

    db.session.expire_all()
    saved_item = db.session.get(AccessReviewItem, other_item_id)
    assert saved_item is not None
    assert saved_item.decision is None

    event = db.session.execute(
        db.select(AuditEvent).where(
            AuditEvent.action == "access_review.decision",
            AuditEvent.target_id == str(other_item_id),
        )
    ).scalar_one_or_none()
    assert event is None


def test_record_access_review_decision_rolls_back_on_audit_failure(
    client, monkeypatch
):
    """
    Verify that an audit failure leaves the review item undecided.
    """
    _login_user(client, [ACCESS_REVIEWER])

    campaign = access_review_service.create_access_review(
        name="Decision campaign",
        created_by_user_id="manager-123",
        reviewer_user_id="test-subject",
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
    campaign_id, item_id = campaign.id, item.id
    db.session.commit()

    fake_audit = Mock(side_effect=AuditPersistenceError("audit_failed"))
    monkeypatch.setattr(
        access_review_service,
        "record_audit_event",
        fake_audit,
    )

    response = client.post(
        f"/access-reviews/{campaign_id}/items/{item_id}/decision",
        data={"decision": "retain"},
    )

    assert response.status_code == 503
    fake_audit.assert_called_once()
    db.session.expire_all()
    saved_item = db.session.get(AccessReviewItem, item_id)
    assert saved_item is not None
    assert saved_item.decision is None


@pytest.mark.parametrize(
    ("reason", "expected_status"),
    [
        ("access_review_not_found", 404),
        ("access_review_item_not_found", 404),
        ("access_review_self_certification", 403),
        ("access_review_not_open", 409),
        ("access_review_item_already_decided", 409),
    ],
)
def test_record_access_review_decision_logs_denial(
    client, monkeypatch, caplog, reason, expected_status
):
    """
    Verify that a denied decision is logged as a structured event with its stable reason.
    """
    _login_user(client, [ACCESS_REVIEWER])

    monkeypatch.setattr(
        governance_routes,
        "record_access_review_decision_with_audit",
        Mock(side_effect=ValueError(reason)),
    )

    with caplog.at_level("WARNING"):
        response = client.post(
            "/access-reviews/7/items/42/decision",
            data={"decision": "retain"},
        )

    assert response.status_code == expected_status

    events = [
        json.loads(record.getMessage())
        for record in caplog.records
        if record.getMessage().startswith("{")
    ]

    assert len(events) == 1
    assert events[0]["event"] == "access_review.decision"
    assert events[0]["outcome"] == "denied"
    assert events[0]["reason"] == reason
    assert events[0]["actor_user_id"] == "test-subject"
    assert events[0]["target_id"] == "42"
    assert events[0]["review_id"] == "7"


def test_record_access_review_decision_returns_400_for_unmapped_error(
    client, monkeypatch, caplog
):
    """
    Verify that an unmapped service error returns HTTP 400 and its message is not logged.
    """
    _login_user(client, [ACCESS_REVIEWER])

    monkeypatch.setattr(
        governance_routes,
        "record_access_review_decision_with_audit",
        Mock(side_effect=ValueError("unexpected detail from a lower layer")),
    )

    with caplog.at_level("WARNING"):
        response = client.post(
            "/access-reviews/7/items/42/decision",
            data={"decision": "retain"},
        )

    assert response.status_code == 400
    assert "unexpected detail from a lower layer" not in caplog.text


@pytest.mark.parametrize("decision", ["retain", "revoke"])
def test_record_access_review_decision_allows_assigned_reviewer_to_decide(
client, decision
):
    """
    Verify that the assigned reviewer can retain or revoke an open review item.
    """

    _login_user(client, [ACCESS_REVIEWER])

    campaign = access_review_service.create_access_review(
            name="Decision campaign",
            created_by_user_id="manager-123",
            reviewer_user_id="test-subject",
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
    campaign_id, item_id = campaign.id, item.id
    db.session.commit()



    response = client.post(
            f"/access-reviews/{campaign_id}/items/{item_id}/decision",
            data={"decision": decision},
        )

    assert response.status_code == 303
    assert response.headers["Location"] == f"/access-reviews/{campaign_id}"
    db.session.expire_all()
    saved_item = db.session.get(AccessReviewItem, item_id)
    assert saved_item is not None
    assert saved_item.decision == decision

    event = db.session.execute(
        db.select(AuditEvent).where(
            AuditEvent.action == "access_review.decision",
            AuditEvent.target_id == str(item_id),
        )
    ).scalar_one_or_none()

    assert event.details["decision"] == decision


def test_record_access_review_decision_rejects_second_decision(client):
    """
    Verify that a second submission cannot change a saved review decision.
    """
    _login_user(client, [ACCESS_REVIEWER])

    campaign = access_review_service.create_access_review(
        name="Decision campaign",
        created_by_user_id="manager-123",
        reviewer_user_id="test-subject",
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

    response = client.post(
        f"/access-reviews/{campaign.id}/items/{item.id}/decision",
        data={"decision": "retain"},)

    response2 = client.post(
        f"/access-reviews/{campaign.id}/items/{item.id}/decision",
        data={"decision": "revoke"},
    )

    assert response.status_code == 303
    assert response2.status_code == 409
    db.session.expire_all()
    saved_item = db.session.get(AccessReviewItem, item.id)
    assert saved_item is not None
    assert saved_item.decision == "retain"

    event = db.session.execute(
        db.select(AuditEvent).where(
            AuditEvent.action == "access_review.decision",
            AuditEvent.target_id == str(item.id),
        )
    ).scalar_one_or_none()

    assert event is not None
    assert event.details["decision"] == "retain"


def _open_campaign_for_test_subject():
    """
    Create an open campaign assigned to the test user with one undecided item, and return both ids.
    """
    campaign = access_review_service.create_access_review(
        name="Decision campaign",
        created_by_user_id="manager-123",
        reviewer_user_id="test-subject",
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
    campaign_id, item_id = campaign.id, item.id
    db.session.commit()
    return campaign_id, item_id


def test_record_access_review_decision_accepts_crlf_comment_within_browser_limit(client):
    """
    Verify that a comment of 1000 browser-counted characters posted with CRLF is stored with newlines.
    """
    _login_user(client, [ACCESS_REVIEWER])
    campaign_id, item_id = _open_campaign_for_test_subject()

    response = client.post(
        f"/access-reviews/{campaign_id}/items/{item_id}/decision",
        data={"decision": "revoke", "comment": "x" + "\r\n" * 5 + "x" * 994},
    )

    assert response.status_code == 303

    db.session.expire_all()
    saved_item = db.session.get(AccessReviewItem, item_id)
    assert saved_item.decision_comment == "x" + "\n" * 5 + "x" * 994
