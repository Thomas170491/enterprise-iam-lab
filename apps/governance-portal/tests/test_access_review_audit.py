from unittest.mock import Mock

import pytest
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import AccessReview, AuditEvent, AccessReviewItem, ManagedRole
import services.access_review_service as access_review_service
from services.exceptions import AuditPersistenceError, KeycloakAdminAPIError


@pytest.fixture
def fake_validate_reviewer(monkeypatch):
    """
    Mock successful reviewer validation without contacting Keycloak.
    """
    validator = Mock(
        return_value={
            "id": "reviewer-456",
            "enabled": True,
        }
    )

    monkeypatch.setattr(
        access_review_service,
        "validate_access_review_reviewer",
        validator,
    )

    return validator


def test_create_access_review_with_audit_records_actor(
    app,
    fake_validate_reviewer,
):
    """
    Verify that campaign creation commits the campaign and its human-actor audit event.
    """
    review = access_review_service.create_access_review_with_audit(
        name="September review",
        created_by_user_id="operator-123",
        actor_username="leo",
        reviewer_user_id="reviewer-456",
        admin_api_url="https://keycloak.test/admin",
        token_url="https://keycloak.test/token",
        client_id="iam-governance-service",
        client_secret="test-secret",
    )
    review_id = review.id

    fake_validate_reviewer.assert_called_once_with(
        reviewer_user_id="reviewer-456",
        admin_api_url="https://keycloak.test/admin",
        token_url="https://keycloak.test/token",
        client_id="iam-governance-service",
        client_secret="test-secret",
    )

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


def test_open_access_review_with_audit_records_actor(app):
    """
    Verify that opening a campaign commits its status and human-actor audit event.
    """
    review = access_review_service.create_access_review(
        name="Manager review",
        created_by_user_id="manager-123",
        reviewer_user_id="reviewer-456",
    )
    access_review_service.add_access_review_item(
        review_id=review.id,
        user_id="user-123",
        username="alice",
        client_name="employee-portal",
        role_id="finance-role-id",
        role_name="finance-data-viewer",
    )
    db.session.commit()

    review_id = review.id

    opened_review = access_review_service.open_access_review_with_audit(
        review_id=review_id,
        manager_user_id="manager-123",
        actor_username="leo",
    )

    db.session.rollback()

    saved_review = db.session.get(AccessReview, review_id)
    event = db.session.execute(
        db.select(AuditEvent).where(
            AuditEvent.action == "access_review.open",
            AuditEvent.target_id == str(review_id),
        )
    ).scalar_one_or_none()

    assert opened_review.id == review_id
    assert saved_review is not None
    assert saved_review.status == "open"
    assert event is not None
    assert event.actor_user_id == "manager-123"
    assert event.actor_username == "leo"
    assert event.target_type == "access_review"
    assert event.target_name == "Manager review"
    assert event.outcome == "success"
    assert event.details["source"] == "governance-portal"
    assert event.details["reviewer_user_id"] == "reviewer-456"
    assert event.details["previous_status"] == "draft"
    assert event.details["new_status"] == "open"
    assert event.details["item_count"] == 1


def test_open_access_review_with_audit_rolls_back_on_audit_failure(app, monkeypatch):
    """
    Verify that an audit failure rolls back campaign opening and preserves its snapshots.
    """
    review = access_review_service.create_access_review(
        name="Manager review",
        created_by_user_id="manager-123",
        reviewer_user_id="reviewer-456",
    )
    access_review_service.add_access_review_item(
        review_id=review.id,
        user_id="user-123",
        username="alice",
        client_name="employee-portal",
        role_id="finance-role-id",
        role_name="finance-data-viewer",
    )
    db.session.commit()

    review_id = review.id
    fake_audit = Mock(side_effect=AuditPersistenceError("audit failed"))
    monkeypatch.setattr(
        access_review_service,
        "record_audit_event",
        fake_audit,
    )

    with pytest.raises(AuditPersistenceError, match="audit failed"):
        access_review_service.open_access_review_with_audit(
            review_id=review_id,
            manager_user_id="manager-123",
            actor_username="leo",
        )

    fake_audit.assert_called_once()

    saved_review = db.session.get(AccessReview, review_id)
    saved_items = (
        db.session.execute(
            db.select(AccessReviewItem).where(
                AccessReviewItem.review_id == review_id,
            )
        )
        .scalars()
        .all()
    )
    open_event = db.session.execute(
        db.select(AuditEvent).where(
            AuditEvent.action == "access_review.open",
            AuditEvent.target_id == str(review_id),
        )
    ).scalar_one_or_none()

    assert saved_review is not None
    assert saved_review.status == "draft"
    assert len(saved_items) == 1
    assert open_event is None


def test_open_access_review_with_audit_rolls_back_on_commit_failure(app, monkeypatch):
    """
    Verify that a failed commit restores draft status and removes the opening audit event.
    """
    review = access_review_service.create_access_review(
        name="Manager review",
        created_by_user_id="manager-123",
        reviewer_user_id="reviewer-456",
    )
    access_review_service.add_access_review_item(
        review_id=review.id,
        user_id="user-123",
        username="alice",
        client_name="employee-portal",
        role_id="finance-role-id",
        role_name="finance-data-viewer",
    )
    db.session.commit()

    review_id = review.id
    monkeypatch.setattr(
        db.session,
        "commit",
        Mock(side_effect=SQLAlchemyError("commit failed")),
    )

    with pytest.raises(SQLAlchemyError, match="commit failed"):
        access_review_service.open_access_review_with_audit(
            review_id=review_id,
            manager_user_id="manager-123",
            actor_username="leo",
        )

    saved_review = db.session.get(AccessReview, review_id)
    saved_items = (
        db.session.execute(
            db.select(AccessReviewItem).where(
                AccessReviewItem.review_id == review_id,
            )
        )
        .scalars()
        .all()
    )
    open_event = db.session.execute(
        db.select(AuditEvent).where(
            AuditEvent.action == "access_review.open",
            AuditEvent.target_id == str(review_id),
        )
    ).scalar_one_or_none()

    assert saved_review is not None
    assert saved_review.status == "draft"
    assert len(saved_items) == 1
    assert open_event is None


def test_open_access_review_with_audit_rejects_other_manager(app):
    """
    Verify that another manager cannot open a campaign or create an opening audit event.
    """
    review = access_review_service.create_access_review(
        name="Manager review",
        created_by_user_id="manager-123",
        reviewer_user_id="reviewer-456",
    )
    access_review_service.add_access_review_item(
        review_id=review.id,
        user_id="user-123",
        username="alice",
        client_name="employee-portal",
        role_id="finance-role-id",
        role_name="finance-data-viewer",
    )
    db.session.commit()

    review_id = review.id

    with pytest.raises(ValueError, match="access_review_not_found"):
        access_review_service.open_access_review_with_audit(
            review_id=review_id,
            manager_user_id="other-manager",
            actor_username="other-manager-user",
        )

    saved_review = db.session.get(AccessReview, review_id)
    saved_items = (
        db.session.execute(
            db.select(AccessReviewItem).where(
                AccessReviewItem.review_id == review_id,
            )
        )
        .scalars()
        .all()
    )
    open_event = db.session.execute(
        db.select(AuditEvent).where(
            AuditEvent.action == "access_review.open",
            AuditEvent.target_id == str(review_id),
        )
    ).scalar_one_or_none()

    assert saved_review is not None
    assert saved_review.status == "draft"
    assert len(saved_items) == 1
    assert open_event is None


def test_create_access_review_with_audit_rolls_back_on_audit_failure(
    app,
    monkeypatch,
    fake_validate_reviewer,
):
    """
    Verify that an audit failure prevents the campaign from being saved.
    """
    fake_audit = Mock(side_effect=AuditPersistenceError("database unavailable"))

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
            admin_api_url="https://keycloak.test/admin",
            token_url="https://keycloak.test/token",
            client_id="iam-governance-service",
            client_secret="test-secret",
        )

    fake_validate_reviewer.assert_called_once()
    fake_audit.assert_called_once()
    assert fake_audit.call_args.kwargs["commit"] is False

    assert db.session.execute(db.select(AccessReview)).scalars().all() == []

    assert db.session.execute(db.select(AuditEvent)).scalars().all() == []


def test_create_access_review_with_audit_rolls_back_on_commit_failure(
    app,
    monkeypatch,
    fake_validate_reviewer,
):
    """
    Verify that a failed commit rolls back both the campaign and its audit event.
    """
    fake_commit = Mock(side_effect=SQLAlchemyError("commit failed"))

    monkeypatch.setattr(
        db.session,
        "commit",
        fake_commit,
    )

    with pytest.raises(SQLAlchemyError, match="commit failed"):
        access_review_service.create_access_review_with_audit(
            name="September review",
            created_by_user_id="operator-123",
            actor_username="leo",
            reviewer_user_id="reviewer-456",
            admin_api_url="https://keycloak.test/admin",
            token_url="https://keycloak.test/token",
            client_id="iam-governance-service",
            client_secret="test-secret",
        )

    fake_validate_reviewer.assert_called_once()
    fake_commit.assert_called_once()

    assert db.session.execute(db.select(AccessReview)).scalars().all() == []

    assert db.session.execute(db.select(AuditEvent)).scalars().all() == []


def test_create_access_review_with_audit_rejects_ineligible_reviewer(
    app,
    fake_validate_reviewer,
):
    """
    Verify that reviewer rejection leaves no campaign or audit event saved.
    """
    fake_validate_reviewer.side_effect = ValueError("reviewer_missing_required_role")

    with pytest.raises(ValueError, match="reviewer_missing_required_role"):
        access_review_service.create_access_review_with_audit(
            name="September review",
            created_by_user_id="operator-123",
            actor_username="leo",
            reviewer_user_id="reviewer-456",
            admin_api_url="https://keycloak.test/admin",
            token_url="https://keycloak.test/token",
            client_id="iam-governance-service",
            client_secret="test-secret",
        )

    fake_validate_reviewer.assert_called_once()

    assert db.session.execute(db.select(AccessReview)).scalars().all() == []

    assert db.session.execute(db.select(AuditEvent)).scalars().all() == []


@pytest.fixture
def population_setup(app, monkeypatch):
    """
    Prepare a saved draft campaign, managed role, and mocked Keycloak responses.
    """
    campaign = access_review_service.create_access_review(
        "September review",
        "manager-123",
        "reviewer-456",
    )

    db.session.add(
        ManagedRole(
            client_name="employee-portal",
            role_name="finance-data-viewer",
            enabled=True,
        )
    )
    db.session.commit()

    fake_get_user = Mock(
        return_value={
            "id": "user-123",
            "username": "alice",
        }
    )
    fake_get_roles = Mock(
        return_value=[
            {
                "id": "finance-role-id",
                "name": "finance-data-viewer",
            }
        ]
    )

    monkeypatch.setattr(
        access_review_service,
        "get_user",
        fake_get_user,
    )
    monkeypatch.setattr(
        access_review_service,
        "get_direct_client_roles",
        fake_get_roles,
    )

    return {
        "arguments": {
            "review_id": campaign.id,
            "manager_user_id": "manager-123",
            "actor_username": "leo",
            "user_id": "user-123",
            "admin_api_url": "https://keycloak.test/admin",
            "token_url": "https://keycloak.test/token",
            "client_id": "iam-governance-service",
            "client_secret": "test-secret",
        },
        "get_user": fake_get_user,
        "get_roles": fake_get_roles,
    }


def test_populate_access_review_with_audit_records_actor(population_setup):
    """
    Verify that population commits captured access and its human-actor audit event.
    """
    arguments = population_setup["arguments"]

    items = access_review_service.populate_access_review_with_audit(**arguments)

    assert len(items) == 1
    item_id = items[0].id
    review_id = arguments["review_id"]

    db.session.rollback()

    saved_item = db.session.get(AccessReviewItem, item_id)
    event = db.session.execute(
        db.select(AuditEvent).where(
            AuditEvent.action == "access_review.populate",
            AuditEvent.target_id == str(review_id),
        )
    ).scalar_one_or_none()

    assert saved_item is not None
    assert saved_item.review_id == review_id
    assert saved_item.user_id == "user-123"
    assert saved_item.role_id == "finance-role-id"

    assert event is not None
    assert event.actor_user_id == "manager-123"
    assert event.actor_username == "leo"
    assert event.target_type == "access_review"
    assert event.outcome == "success"
    assert event.details["source"] == "governance-portal"
    assert event.details["user_id"] == "user-123"
    assert event.details["client_name"] == "employee-portal"
    assert event.details["items_added"] == 1


def test_populate_access_review_with_audit_records_zero_new_items(
    population_setup,
):
    """
    Verify that repeated population records zero additions without duplicating snapshots.
    """
    arguments = population_setup["arguments"]

    access_review_service.populate_access_review_with_audit(**arguments)
    second_items = access_review_service.populate_access_review_with_audit(**arguments)

    assert second_items == []

    db.session.rollback()

    saved_items = (
        db.session.execute(
            db.select(AccessReviewItem).where(
                AccessReviewItem.review_id == arguments["review_id"],
            )
        )
        .scalars()
        .all()
    )

    events = (
        db.session.execute(
            db.select(AuditEvent)
            .where(
                AuditEvent.action == "access_review.populate",
                AuditEvent.target_id == str(arguments["review_id"]),
            )
            .order_by(AuditEvent.id)
        )
        .scalars()
        .all()
    )

    assert len(saved_items) == 1
    assert len(events) == 2
    assert events[0].details["items_added"] == 1
    assert events[1].details["items_added"] == 0
    assert events[1].outcome == "success"


@pytest.mark.parametrize("failure_stage", ["audit", "commit"])
def test_populate_access_review_with_audit_rolls_back_on_persistence_failure(
    population_setup,
    monkeypatch,
    failure_stage,
):
    """
    Verify that audit or commit failure rolls back snapshots and population audit events.
    """
    arguments = population_setup["arguments"]

    if failure_stage == "audit":
        expected_error = AuditPersistenceError
        failure_mock = Mock(side_effect=AuditPersistenceError("audit failed"))
        monkeypatch.setattr(
            access_review_service,
            "record_audit_event",
            failure_mock,
        )
    else:
        expected_error = SQLAlchemyError
        failure_mock = Mock(side_effect=SQLAlchemyError("commit failed"))
        monkeypatch.setattr(
            db.session,
            "commit",
            failure_mock,
        )

    with pytest.raises(expected_error, match=f"{failure_stage} failed"):
        access_review_service.populate_access_review_with_audit(**arguments)

    failure_mock.assert_called_once()

    if failure_stage == "audit":
        assert failure_mock.call_args.kwargs["commit"] is False

    # The campaign existed before the failed population transaction.
    campaign = db.session.get(AccessReview, arguments["review_id"])
    assert campaign is not None
    assert campaign.status == "draft"

    assert (
        db.session.execute(
            db.select(AccessReviewItem).where(
                AccessReviewItem.review_id == arguments["review_id"],
            )
        )
        .scalars()
        .all()
        == []
    )

    assert (
        db.session.execute(
            db.select(AuditEvent).where(
                AuditEvent.action == "access_review.populate",
                AuditEvent.target_id == str(arguments["review_id"]),
            )
        )
        .scalars()
        .all()
        == []
    )


def test_populate_access_review_with_audit_propagates_keycloak_failure(
    population_setup,
    monkeypatch,
):
    """
    Verify that a Keycloak failure saves no snapshots and records no success audit event.
    """
    arguments = population_setup["arguments"]
    population_setup["get_roles"].side_effect = KeycloakAdminAPIError(
        "Role retrieval failed"
    )

    fake_audit = Mock()
    fake_commit = Mock()

    monkeypatch.setattr(
        access_review_service,
        "record_audit_event",
        fake_audit,
    )
    monkeypatch.setattr(
        db.session,
        "commit",
        fake_commit,
    )

    with pytest.raises(KeycloakAdminAPIError, match="Role retrieval failed"):
        access_review_service.populate_access_review_with_audit(**arguments)

    fake_audit.assert_not_called()
    fake_commit.assert_not_called()

    assert (
        db.session.execute(
            db.select(AccessReviewItem).where(
                AccessReviewItem.review_id == arguments["review_id"],
            )
        )
        .scalars()
        .all()
        == []
    )

    assert (
        db.session.execute(
            db.select(AuditEvent).where(
                AuditEvent.action == "access_review.populate",
                AuditEvent.target_id == str(arguments["review_id"]),
            )
        )
        .scalars()
        .all()
        == []
    )
