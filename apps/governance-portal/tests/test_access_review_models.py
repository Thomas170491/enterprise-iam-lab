import pytest

from extensions import db
from models import AccessReview, AccessReviewItem
from sqlalchemy.exc import IntegrityError


def _decided_item(decision, remediation_status, decision_comment=None):
    """
    Build an access review item with the given decision and remediation status.
    """
    review = AccessReview(
        name="test_review",
        created_by_user_id="testuser1",
        reviewer_user_id="testuser2",
    )
    item = AccessReviewItem(
        review=review,
        user_id="testuser3",
        username="testuser",
        client_name="employee-portal",
        role_name="testrole",
        role_id="fake-id",
        assignment_source="direct",
        decision=decision,
        remediation_status=remediation_status,
        decision_comment=decision_comment,
    )
    db.session.add_all([review, item])
    return item

def test_access_review_defaults_to_draft(app):
    """
    Verify that a new access review defaults to draft and receives creation timestamps.
    """

    access_review = AccessReview(
        name="test_review", created_by_user_id="testuser1", reviewer_user_id="testuser2"
    )

    db.session.add(access_review)
    db.session.flush()

    assert access_review.id is not None
    assert access_review.status == "draft"
    assert access_review.created_at is not None
    assert access_review.updated_at is not None


def test_access_review_item_links_to_review(app):
    """
    Verify that an access review item belongs to its campaign and preserves identity and role details.
    """

    access_review = AccessReview(
        name="test_review", created_by_user_id="testuser1", reviewer_user_id="testuser2"
    )

    access_review_item = AccessReviewItem(
        review=access_review,
        user_id="testuser31",
        username="testuser",
        client_name="employee-portal",
        role_name="testrole",
        role_id="fake-id",
        assignment_source="direct",
    )

    db.session.add_all([access_review, access_review_item])
    db.session.flush()

    assert access_review_item.review_id == access_review.id
    assert access_review_item.review is access_review
    assert access_review_item in access_review.items
    assert access_review_item.role_name == "testrole"


def test_access_review_rejects_invalid_status(app):
    """
    Verify that the database rejects an access review with an unsupported status.
    """

    access_review = AccessReview(
        name="test_review",
        created_by_user_id="testuser1",
        reviewer_user_id="testuser2",
        status="invalid",
    )

    db.session.add(access_review)

    with pytest.raises(IntegrityError):
        db.session.flush()

    db.session.rollback()


def test_access_review_item_rejects_invalid_assignment_source(app):
    """
    Verify that the database rejects an invalid assignment source.
    """

    access_review = AccessReview(
        name="test_review",
        created_by_user_id="testuser1",
        reviewer_user_id="testuser2",
    )

    access_review_item = AccessReviewItem(
        review=access_review,
        user_id="testuser31",
        username="testuser",
        client_name="employee-portal",
        role_name="testrole",
        role_id="fake-id",
        assignment_source="unknown",
    )

    db.session.add_all([access_review, access_review_item])

    with pytest.raises(IntegrityError, match="ck_access_review_items_valid_assignment_source",):
        db.session.flush()

    db.session.rollback()


def test_access_review_rejects_duplicate_items(app):
    """
    Verify that a campaign cannot contain duplicate entries for the same identity, client, and role.
    """

    access_review = AccessReview(
        name="test_review", created_by_user_id="testuser1", reviewer_user_id="testuser2"
    )

    access_review_item = AccessReviewItem(
        review=access_review,
        user_id="testuser31",
        username="testuser",
        client_name="employee-portal",
        role_name="testrole",
        role_id="fake-id",
        assignment_source="direct",
    )

    db.session.add_all([access_review, access_review_item])
    db.session.flush()

    access_review_item2 = AccessReviewItem(
        review=access_review,
        user_id="testuser31",
        username="testuser",
        client_name="employee-portal",
        role_name="testrole",
        role_id="fake-id",
        assignment_source="direct",
    )

    db.session.add(access_review_item2)

    with pytest.raises(IntegrityError):
        db.session.flush()

    db.session.rollback()
    
@pytest.mark.parametrize(
    "decision, remediation_status",
    [
        (None, None),
        ("retain", "not_required"),
        ("revoke", "pending"),
        ("revoke", "completed"),
        ("revoke", "incomplete"),
    ],
)
def test_access_review_item_accepts_consistent_remediation_status(app, decision, remediation_status):
    """
    Verify that each decision accepts only its matching remediation statuses.
    """
    _decided_item(decision, remediation_status)
    db.session.flush()

@pytest.mark.parametrize(
    "decision, remediation_status",
    [
        (None, "pending"),          # undecided but already remediating
        ("retain", None),           # decided with no status
        ("retain", "pending"),      # retained access must not be remediated
        ("revoke", None),
        ("revoke", "not_required"),
        ("revoke", "unknown"),
    ],
)
def test_access_review_item_rejects_inconsistent_remediation_status(app, decision, remediation_status):
    """
    Verify that the database rejects a remediation status that does not match the decision.
    """
    _decided_item(decision, remediation_status)

    with pytest.raises(IntegrityError, match="ck_access_review_items_valid_remediation_status"):
        db.session.flush()

    db.session.rollback()

def test_access_review_item_stores_full_length_decision_comment(app):
    """
    Verify that a decision comment of the maximum length is stored unchanged.
    """
    comment = "x" * 1000

    item = _decided_item("revoke", "pending", decision_comment=comment)
    db.session.commit()

    db.session.expire_all()
    saved = db.session.get(AccessReviewItem, item.id)

    assert saved.decision_comment == comment

