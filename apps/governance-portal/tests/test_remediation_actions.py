from unittest.mock import Mock

import pytest

import services.access_review_service as access_review_service
import services.remediation_service as remediation_service
from extensions import db
from models import AccessReviewItem, AuditEvent
from services.exceptions import (
    AuditPersistenceError,
    KeycloakAdminAPIError,
    RoleAdministrationPolicyError,
)

MANAGER_ID = "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d"
REVIEWER_ID = "7a1d2c3b-4e5f-4a6b-8c7d-9e0f1a2b3c4d"
USER_ID = "5c6d7e8f-1a2b-4c3d-8e9f-0a1b2c3d4e5f"
ROLE_ID = "finance-role-id"
KEYCLOAK_ARGS = {
    "admin_api_url": "https://keycloak.test/admin/realms/novasecure",
    "token_url": "https://keycloak.test/token",
    "client_id": "iam-governance-service",
    "client_secret": "fake-secret",
}

DIRECT_ONLY = {
    "drift": "none",
    "direct_grant_present": True,
    "other_grants_present": False,
}
DIRECT_AND_GROUP = {
    "drift": "sources_changed",
    "direct_grant_present": True,
    "other_grants_present": True,
}
GROUP_ONLY = {
    "drift": "sources_changed",
    "direct_grant_present": False,
    "other_grants_present": True,
}
ROLE_REMOVED = {
    "drift": "role_removed",
    "direct_grant_present": False,
    "other_grants_present": False,
}


def _campaign_with_decided_item(decision="revoke"):
    """
    Create an open campaign owned by MANAGER_ID with one item decided by REVIEWER_ID, and return both ids.
    """
    campaign = access_review_service.create_access_review(
        name="Remediation campaign",
        created_by_user_id=MANAGER_ID,
        reviewer_user_id=REVIEWER_ID,
    )
    item = access_review_service.add_access_review_item(
        review_id=campaign.id,
        user_id=USER_ID,
        username="alice",
        client_name="employee-portal",
        role_id=ROLE_ID,
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


def _patch_keycloak(monkeypatch, assessments, remove_side_effect=None):
    """
    Replace live-access reads with the given assessments, in order, and role removal with a mock.
    """
    fake_assess = Mock(side_effect=assessments)
    fake_remove = Mock(side_effect=remove_side_effect)
    monkeypatch.setattr(remediation_service, "get_live_access_assessment", fake_assess)
    monkeypatch.setattr(remediation_service, "remove_identity_client_role", fake_remove)
    return fake_assess, fake_remove


def _remediate(review_id, item_id, manager_user_id=MANAGER_ID):
    """
    Run remediation for one item as the given manager.
    """
    return remediation_service.remediate_access_review_item_with_audit(
        review_id=review_id,
        item_id=item_id,
        manager_user_id=manager_user_id,
        actor_username="manager",
        **KEYCLOAK_ARGS,
    )


def _saved_item(item_id):
    """
    Reload an item from the database.
    """
    db.session.expire_all()
    return db.session.get(AccessReviewItem, item_id)


def _remediation_events():
    """
    Return every committed remediation audit event.
    """
    return (
        db.session.execute(
            db.select(AuditEvent).where(AuditEvent.action == "access_review.remediation")
        )
        .scalars()
        .all()
    )


def test_remediation_removes_direct_role_and_completes(app, monkeypatch):
    """
    Verify that a direct-only revoked role is removed by ID-checked removal and the item completes.
    """
    review_id, item_id = _campaign_with_decided_item()
    fake_assess, fake_remove = _patch_keycloak(monkeypatch, [DIRECT_ONLY, ROLE_REMOVED])

    _remediate(review_id, item_id)

    fake_remove.assert_called_once_with(
        **KEYCLOAK_ARGS,
        user_id=USER_ID,
        target_client_name="employee-portal",
        role_name="finance-data-viewer",
        actor_user_id=MANAGER_ID,
        actor_username="manager",
        expected_role_id=ROLE_ID,
    )
    assert fake_assess.call_count == 2
    assert _saved_item(item_id).remediation_status == "completed"

    events = _remediation_events()
    assert len(events) == 1
    assert events[0].actor_user_id == MANAGER_ID
    assert events[0].target_id == str(item_id)
    assert events[0].outcome == "success"
    assert events[0].details["action"] == "direct_role_removed"
    assert events[0].details["drift"] == "none"
    assert events[0].details["remediation_status"] == "completed"
    assert events[0].details["service_client"] == "iam-governance-service"


def test_remediation_marks_incomplete_when_another_grant_remains(app, monkeypatch):
    """
    Verify that removing the direct role while a group still grants it leaves the item incomplete.
    """
    review_id, item_id = _campaign_with_decided_item()
    _, fake_remove = _patch_keycloak(monkeypatch, [DIRECT_AND_GROUP, GROUP_ONLY])

    _remediate(review_id, item_id)

    fake_remove.assert_called_once()
    assert _saved_item(item_id).remediation_status == "incomplete"
    assert _remediation_events()[0].details["action"] == "direct_role_removed"
    assert _remediation_events()[0].details["drift"] == "sources_changed"


def test_remediation_completes_without_keycloak_write_when_role_already_removed(
    app, monkeypatch
):
    """
    Verify that a role no longer effective completes the item without removing anything.
    """
    review_id, item_id = _campaign_with_decided_item()
    fake_assess, fake_remove = _patch_keycloak(monkeypatch, [ROLE_REMOVED])

    _remediate(review_id, item_id)

    fake_remove.assert_not_called()
    assert fake_assess.call_count == 1
    assert _saved_item(item_id).remediation_status == "completed"
    assert _remediation_events()[0].details["action"] == "already_removed"


def test_remediation_requires_manual_action_without_direct_grant(app, monkeypatch):
    """
    Verify that a role held only through other grants is left incomplete without any Keycloak write.
    """
    review_id, item_id = _campaign_with_decided_item()
    _, fake_remove = _patch_keycloak(monkeypatch, [GROUP_ONLY])

    _remediate(review_id, item_id)

    fake_remove.assert_not_called()
    assert _saved_item(item_id).remediation_status == "incomplete"
    assert _remediation_events()[0].details["action"] == "manual_required"


def test_remediation_refuses_retained_item(app, monkeypatch):
    """
    Verify that a retained item cannot be remediated and Keycloak is never contacted.
    """
    review_id, item_id = _campaign_with_decided_item(decision="retain")
    fake_assess, fake_remove = _patch_keycloak(monkeypatch, [DIRECT_ONLY])

    with pytest.raises(ValueError, match="^access_review_item_not_pending_remediation$"):
        _remediate(review_id, item_id)

    fake_assess.assert_not_called()
    fake_remove.assert_not_called()
    assert _remediation_events() == []


def test_remediation_refuses_item_already_remediated(app, monkeypatch):
    """
    Verify that an item whose remediation already finished cannot be remediated again.
    """
    review_id, item_id = _campaign_with_decided_item()
    _patch_keycloak(monkeypatch, [ROLE_REMOVED])
    _remediate(review_id, item_id)

    fake_assess, fake_remove = _patch_keycloak(monkeypatch, [DIRECT_ONLY])

    with pytest.raises(ValueError, match="^access_review_item_not_pending_remediation$"):
        _remediate(review_id, item_id)

    fake_assess.assert_not_called()
    fake_remove.assert_not_called()
    assert len(_remediation_events()) == 1


def test_remediation_hides_campaign_from_other_manager(app, monkeypatch):
    """
    Verify that another manager gets not-found and Keycloak is never contacted.
    """
    review_id, item_id = _campaign_with_decided_item()
    fake_assess, fake_remove = _patch_keycloak(monkeypatch, [DIRECT_ONLY])

    with pytest.raises(ValueError, match="^access_review_not_found$"):
        _remediate(review_id, item_id, manager_user_id="9c8b7a6d-5e4f-4a3b-9c2d-1e0f2a3b4c5d")

    fake_assess.assert_not_called()
    fake_remove.assert_not_called()


def test_remediation_refuses_item_from_another_campaign(app, monkeypatch):
    """
    Verify that an item outside the named campaign is not found.
    """
    review_id, _ = _campaign_with_decided_item()
    other_review_id, other_item_id = _campaign_with_decided_item()
    assert other_review_id != review_id
    fake_assess, _ = _patch_keycloak(monkeypatch, [DIRECT_ONLY])

    with pytest.raises(ValueError, match="^access_review_item_not_found$"):
        _remediate(review_id, other_item_id)

    fake_assess.assert_not_called()


def test_remediation_refuses_cancelled_campaign(app, monkeypatch):
    """
    Verify that revoked items in a cancelled campaign are not remediated.
    """
    review_id, item_id = _campaign_with_decided_item()
    access_review_service.cancel_access_review(review_id)
    db.session.commit()
    fake_assess, fake_remove = _patch_keycloak(monkeypatch, [DIRECT_ONLY])

    with pytest.raises(ValueError, match="^access_review_not_open$"):
        _remediate(review_id, item_id)

    fake_assess.assert_not_called()
    fake_remove.assert_not_called()


@pytest.mark.parametrize(
    "error",
    [
        AuditPersistenceError("initial audit failed"),
        KeycloakAdminAPIError("removal failed"),
        RoleAdministrationPolicyError("role_id_mismatch"),
    ],
    ids=["initial_audit_failure", "keycloak_failure", "role_id_mismatch"],
)
def test_remediation_leaves_item_pending_when_removal_fails(app, monkeypatch, error):
    """
    Verify that a failed or refused removal propagates and leaves the item pending with no remediation event.
    """
    review_id, item_id = _campaign_with_decided_item()
    fake_assess, _ = _patch_keycloak(monkeypatch, [DIRECT_ONLY], remove_side_effect=error)

    with pytest.raises(type(error)):
        _remediate(review_id, item_id)

    assert fake_assess.call_count == 1
    assert _saved_item(item_id).remediation_status == "pending"
    assert _remediation_events() == []


@pytest.mark.parametrize(
    "error",
    [KeycloakAdminAPIError("Keycloak unavailable"), ValueError("role_source_untraceable")],
    ids=["keycloak_failure", "untraceable"],
)
def test_remediation_leaves_item_pending_when_live_access_cannot_be_read(
    app, monkeypatch, error
):
    """
    Verify that an unreadable live state stops remediation before any Keycloak write.
    """
    review_id, item_id = _campaign_with_decided_item()
    _, fake_remove = _patch_keycloak(monkeypatch, error)

    with pytest.raises(type(error)):
        _remediate(review_id, item_id)

    fake_remove.assert_not_called()
    assert _saved_item(item_id).remediation_status == "pending"


def test_remediation_leaves_item_pending_when_recheck_fails(app, monkeypatch):
    """
    Verify that a failed recheck after removal leaves the item pending, so a retry can finish it.
    """
    review_id, item_id = _campaign_with_decided_item()
    _, fake_remove = _patch_keycloak(
        monkeypatch, [DIRECT_ONLY, KeycloakAdminAPIError("Keycloak unavailable")]
    )

    with pytest.raises(KeycloakAdminAPIError):
        _remediate(review_id, item_id)

    fake_remove.assert_called_once()
    assert _saved_item(item_id).remediation_status == "pending"
    assert _remediation_events() == []


def test_remediation_rolls_back_status_when_remediation_audit_fails(app, monkeypatch):
    """
    Verify that the status change and its audit event are saved together or not at all.
    """
    review_id, item_id = _campaign_with_decided_item()
    _patch_keycloak(monkeypatch, [ROLE_REMOVED])
    monkeypatch.setattr(
        remediation_service,
        "record_audit_event",
        Mock(side_effect=AuditPersistenceError("audit unavailable")),
    )

    with pytest.raises(AuditPersistenceError):
        _remediate(review_id, item_id)

    assert _saved_item(item_id).remediation_status == "pending"
    assert _remediation_events() == []
