from unittest.mock import Mock

import pytest
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import AccessReview, AuditEvent
import services.access_review_service as access_review_service
from services.exceptions import AuditPersistenceError


def test_create_access_review_with_audit_records_actor(app):
    """
    Verify that campaign creation commits the campaign and its human-actor audit event.
    """
    review = access_review_service.create_access_review_with_audit(
        name="September review",
        created_by_user_id="operator-123",
        actor_username="leo",
        reviewer_user_id="reviewer-456",
    )
    review_id = review.id

    # End any transaction started by reading the returned object.
    # Committed records must survive this rollback.
    db.session.rollback()

    saved_review = db.session.get(AccessReview, review_id)
    event = db.session.execute(
        db.select(AuditEvent).where(
            AuditEvent.action == "access_review.create",
            AuditEvent.target_id == str(review_id),
        )
    ).scalar_one_or_none()

    assert saved_review is not None
    assert saved_review.name == "September review"
    assert saved_review.status == "draft"
    assert saved_review.created_by_user_id == "operator-123"
    assert saved_review.reviewer_user_id == "reviewer-456"

    assert event is not None
    assert event.actor_user_id == "operator-123"
    assert event.actor_username == "leo"
    assert event.target_type == "access_review"
    assert event.target_name == "September review"
    assert event.outcome == "success"
    assert event.details["source"] == "governance-portal"
    assert event.details["reviewer_user_id"] == "reviewer-456"
    assert event.details["status"] == "draft"


def test_create_access_review_with_audit_rolls_back_on_audit_failure(
    app,
    monkeypatch,
):
    """
    Verify that an audit failure prevents the campaign from being saved.
    """
    fake_audit = Mock(
        side_effect=AuditPersistenceError("database unavailable")
    )
    monkeypatch.setattr(
        access_review_service,
        "record_audit_event",
        fake_audit,
    )

    with pytest.raises(AuditPersistenceError, match="database unavailable"):
        access_review_service.create_access_review_with_audit(
            name="September review",
            created_by_user_id="operator-123",
            actor_username="leo",
            reviewer_user_id="reviewer-456",
        )

    fake_audit.assert_called_once()
    assert fake_audit.call_args.kwargs["commit"] is False

    assert db.session.execute(
        db.select(AccessReview)
    ).scalars().all() == []

    assert db.session.execute(
        db.select(AuditEvent)
    ).scalars().all() == []


def test_create_access_review_with_audit_rolls_back_on_commit_failure(
    app,
    monkeypatch,
):
    """
    Verify that a failed commit rolls back both the campaign and its audit event.
    """
    monkeypatch.setattr(
        db.session,
        "commit",
        Mock(side_effect=SQLAlchemyError("commit failed")),
    )

    with pytest.raises(SQLAlchemyError, match="commit failed"):
        access_review_service.create_access_review_with_audit(
            name="September review",
            created_by_user_id="operator-123",
            actor_username="leo",
            reviewer_user_id="reviewer-456",
        )

    assert db.session.execute(
        db.select(AccessReview)
    ).scalars().all() == []

    assert db.session.execute(
        db.select(AuditEvent)
    ).scalars().all() == []