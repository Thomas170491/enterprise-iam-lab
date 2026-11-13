from datetime import datetime, timezone
import pytest

from extensions import db
from models import AccessReviewItem, AuditEvent
import services.access_review_service as access_review_service

REVIEWER_ID = "7a1d2c3b-4e5f-4a6b-8c7d-9e0f1a2b3c4d"

def _open_campaign_with_item():
    """
    Create an open campaign assigned to REVIEWER_ID with one undecided item, and return both ids.
    """
    campaign = access_review_service.create_access_review(
        name="Decision campaign",
        created_by_user_id="manager-123",
        reviewer_user_id=REVIEWER_ID,
    )
    item = access_review_service.add_access_review_item(
        review_id=campaign.id,
        user_id="5c6d7e8f-1a2b-4c3d-8e9f-0a1b2c3d4e5f",
        username="alice",
        client_name="employee-portal",
        role_id="finance-role-id",
        role_name="finance-data-viewer",
    )
    access_review_service.open_access_review(campaign.id)
    db.session.commit()
    return campaign.id, item.id

@pytest.mark.parametrize(
    "decision, expected_status",
    [("retain", "not_required"), ("revoke", "pending")],
)
def test_record_access_review_decision_sets_remediation_status(app, decision, expected_status):
    """
    Verify that retain needs no remediation and revoke is left pending remediation.
    """
    review_id, item_id = _open_campaign_with_item()

    access_review_service.record_access_review_decision_with_audit(
        review_id=review_id,
        item_id=item_id,
        reviewer_user_id=REVIEWER_ID,
        actor_username="reviewer",
        decision=decision,
    )

    db.session.expire_all()
    saved = db.session.get(AccessReviewItem, item_id)
    assert saved.remediation_status == expected_status

def test_record_access_review_decision_audits_remediation_status_without_comment(app):
    """
    Verify that the decision audit event records the remediation status but never the comment text.
    """
    review_id, item_id = _open_campaign_with_item()

    access_review_service.record_access_review_decision_with_audit(
        review_id=review_id,
        item_id=item_id,
        reviewer_user_id=REVIEWER_ID,
        actor_username="reviewer",
        decision="revoke",
        comment="moved to Security in October",
    )

    event = db.session.execute(
        db.select(AuditEvent).where(
            AuditEvent.action == "access_review.decision",
            AuditEvent.target_id == str(item_id),
        )
    ).scalar_one()

    assert event.details["remediation_status"] == "pending"
    assert "comment" not in event.details
    assert "moved to Security" not in str(event.details)


@pytest.mark.parametrize(
    "comment",
    [None, "", "   "],
    ids=["none", "empty", "spaces"],
)
def test_record_access_review_decision_stores_blank_comment_as_none(app, comment):
    """
    Verify that a missing, empty or whitespace-only comment is stored as None.
    """
    review_id, item_id = _open_campaign_with_item()

    access_review_service.record_access_review_decision_with_audit(
        review_id=review_id,
        item_id=item_id,
        reviewer_user_id=REVIEWER_ID,
        actor_username="reviewer",
        decision="retain",
        comment=comment,
    )

    db.session.expire_all()
    saved = db.session.get(AccessReviewItem, item_id)
    assert saved.decision_comment is None

@pytest.mark.parametrize(
    "comment, expected",
    [
        ("  needs it for Q4 close  ", "needs it for Q4 close"),
        ("x" * 1000, "x" * 1000),
    ],
    ids=["trimmed", "max_length"],
)
def test_record_access_review_decision_stores_trimmed_comment(app, comment, expected):
    """
    Verify that a decision comment is stored trimmed, up to the 1000-character limit.
    """
    review_id, item_id = _open_campaign_with_item()

    access_review_service.record_access_review_decision_with_audit(
        review_id=review_id,
        item_id=item_id,
        reviewer_user_id=REVIEWER_ID,
        actor_username="reviewer",
        decision="revoke",
        comment=comment,
    )

    db.session.expire_all()
    saved = db.session.get(AccessReviewItem, item_id)
    assert saved.decision_comment == expected


@pytest.mark.parametrize(
    "bad_comment", 
    ["x" * 1001, 123,["list"]],
    ids= ["too_long", "int", "list"]
)
def test_record_access_review_decision_rejects_invalid_comment(app, bad_comment):
    """
    Verify that an overlong or non-string comment is rejected and no decision or audit event is saved.
    """
    review_id, item_id = _open_campaign_with_item()

    with pytest.raises(ValueError, match="^invalid_access_review_comment$"):
        access_review_service.record_access_review_decision_with_audit(
            review_id=review_id,
            item_id=item_id,
            reviewer_user_id=REVIEWER_ID,
            actor_username="reviewer",
            decision="revoke",
            comment=bad_comment,
        )

    db.session.expire_all()
    saved = db.session.get(AccessReviewItem, item_id)
    assert saved.decision is None
    assert saved.remediation_status is None
    assert db.session.execute(db.select(AuditEvent)).scalars().all() == []

def test_record_access_review_decision_does_not_overwrite_concurrent_decision(app):
    """
    Verify that a decision recorded by another request first is kept, even when this one read the item as undecided.
    """
    review_id, item_id = _open_campaign_with_item()

    # This request reads the item while it is still undecided...
    stale_item = db.session.get(AccessReviewItem, item_id)
    assert stale_item.decision is None

    # ...then another request decides it, without this session's copy noticing.
    db.session.execute(
        db.update(AccessReviewItem)
        .where(AccessReviewItem.id == item_id)
        .values(
            decision="retain",
            remediation_status="not_required",
            decided_by_user_id=REVIEWER_ID,
            decided_at=datetime.now(timezone.utc),
        )
        .execution_options(synchronize_session=False)
    )
    assert stale_item.decision is None

    with pytest.raises(ValueError, match="^access_review_item_already_decided$"):
        access_review_service.record_access_review_decision(
            review_id=review_id,
            item_id=item_id,
            reviewer_user_id=REVIEWER_ID,
            decision="revoke",
        )

    db.session.expire_all()
    saved = db.session.get(AccessReviewItem, item_id)
    assert saved.decision == "retain"
    assert saved.remediation_status == "not_required"


def test_record_access_review_decision_locks_campaign_row_shared(app, monkeypatch):
    """
    Verify that the campaign lookup requests a shared row lock (FOR SHARE); SQLite cannot show blocking.
    """
    review_id, item_id = _open_campaign_with_item()

    selects = []
    real_execute = db.session.execute

    def capture(statement, *args, **kwargs):
        selects.append(statement)
        return real_execute(statement, *args, **kwargs)

    monkeypatch.setattr(db.session, "execute", capture)

    access_review_service.record_access_review_decision(
        review_id=review_id,
        item_id=item_id,
        reviewer_user_id=REVIEWER_ID,
        decision="retain",
    )

    campaign_selects = [
        s for s in selects
        if getattr(s, "is_select", False)
        and s.column_descriptions
        and s.column_descriptions[0]["entity"].__name__ == "AccessReview"
    ]
    assert len(campaign_selects) == 1
    lock = campaign_selects[0]._for_update_arg
    assert lock is not None
    assert lock.read is True
