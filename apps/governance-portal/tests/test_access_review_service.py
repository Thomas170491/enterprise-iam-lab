import pytest
from datetime import datetime, timezone


from extensions import db
from models import AccessReview, AccessReviewItem, ManagedRole
from unittest.mock import Mock
from services.exceptions import KeycloakAdminAPIError
import services.access_review_service as access_review_service
import services.keycloak_admin_service as admin_service

# Keep the test helpers explicit while allowing the tests below to use the
# service function by its short name.
create_access_review = access_review_service.create_access_review
add_access_review_item = access_review_service.add_access_review_item
open_access_review = access_review_service.open_access_review
cancel_access_review = access_review_service.cancel_access_review
get_access_reviews_for_reviewer = access_review_service.get_access_reviews_for_reviewer
get_access_review_for_reviewer = access_review_service.get_access_review_for_reviewer
get_access_reviews_for_manager = access_review_service.get_access_reviews_for_manager
get_access_review_for_manager = access_review_service.get_access_review_for_manager
validate_access_review_reviewer = access_review_service.validate_access_review_reviewer


def test_create_access_review(app):
    """
    Verify that creating an access review trims its inputs and returns a draft campaign.
    """

    review = create_access_review(
        " name string ", " created by Thomas ", " reviewer Agnes "
    )

    assert review.id is not None
    assert review.due_at is None
    assert review.name == "name string"
    assert review.created_by_user_id == "created by Thomas"
    assert review.reviewer_user_id == "reviewer Agnes"
    assert review.status == "draft"


def test_create_access_review_rejects_blank_name(app):
    """
    Verify that a whitspaced-only campaign name is rejected
    """

    with pytest.raises(ValueError, match="invalid_review_name"):
        create_access_review(" ", "creator-123", "reviewer-123")


def test_create_access_review_rejects_naive_due_at(app):
    """
    Verify that a due date without timezone information is rejected.
    """

    date = datetime(2026, 12, 1)

    with pytest.raises(ValueError, match="invalid_due_at"):
        create_access_review("name", "id1", "id2", date)


def test_create_access_review_preserves_aware_due_at(app):
    """
    Verify that a timezone-aware due date is preserved when creating a campaign.
    """

    date = datetime(2026, 12, 1, tzinfo=timezone.utc)

    result = create_access_review("name", "id1", "id2", date)

    assert result.due_at == date


def test_create_access_review_does_not_commit(app):
    """
    Verify that rolling back removes the campaign created by the service.
    """

    review = create_access_review(
        name="September review",
        created_by_user_id="creator-123",
        reviewer_user_id="reviewer-456",
    )

    review_id = review.id

    db.session.rollback()

    assert db.session.get(AccessReview, review_id) is None


def test_add_access_review_item_creates_snapshot(app):
    """
    Verify that adding a snapshot preserves its campaign, identity, and role details.
    """

    review = create_access_review(
        name="September review",
        created_by_user_id="creator-123",
        reviewer_user_id="reviewer-456",
    )

    item = add_access_review_item(
        review_id=review.id,
        user_id="  user-123  ",
        username="  alice  ",
        client_name="  employee-portal  ",
        role_id="  finance-role-id  ",
        role_name="  finance-data-viewer  ",
    )

    assert item.id is not None
    assert item.review_id == review.id
    assert item.user_id == "user-123"
    assert item.username == "alice"
    assert item.client_name == "employee-portal"
    assert item.role_id == "finance-role-id"
    assert item.role_name == "finance-data-viewer"


def test_add_access_review_item_defaults_to_direct(app):
    """
    Verify that a snapshot defaults to a direct assignment source.
    """

    review = create_access_review(
        name="September review",
        created_by_user_id="creator-123",
        reviewer_user_id="reviewer-456",
    )

    item = add_access_review_item(
        review_id=review.id,
        user_id="  user-123  ",
        username="  alice  ",
        client_name="  employee-portal  ",
        role_id="  finance-role-id  ",
        role_name="  finance-data-viewer  ",
    )

    assert item.assignment_source == "direct"
    
@pytest.mark.parametrize("assignment_source", ["direct", "inherited", "both"])
def test_add_access_review_item_preserves_assignment_source(app, assignment_source):
    """
    Verify that a snapshot preserves its supplied assignment source.
    """
    
    review = create_access_review(
        name="September review",
        created_by_user_id="creator-123",
        reviewer_user_id="reviewer-456",
    )
    
    item = add_access_review_item(
        review_id=review.id,
        user_id="  user-123  ",
        username="  alice  ",
        client_name="  employee-portal  ",
        role_id="  finance-role-id  ",
        role_name="  finance-data-viewer  ",
        assignment_source= assignment_source,
    )
    
    assert item.assignment_source == assignment_source
    
@pytest.mark.parametrize("assignment_source", ["unknown", "", None])
def test_add_access_review_item_rejects_invalid_assignment_source(
    app, assignment_source
):
    """
    Verify that an invalid assignment source is rejected without saving an item.
    """
    
    review = create_access_review(
        name="September review",
        created_by_user_id="creator-123",
        reviewer_user_id="reviewer-456",
    )
    with pytest.raises(ValueError, match="invalid_assignment_source"):
        add_access_review_item(
            review_id=review.id,
            user_id="  user-123  ",
            username="  alice  ",
            client_name="  employee-portal  ",
            role_id="  finance-role-id  ",
            role_name="  finance-data-viewer  ",
            assignment_source= assignment_source,
        )
        
    items = db.session.execute(
        db.select(AccessReviewItem)
        .where(
            AccessReviewItem.review_id== review.id
                )).scalars().all()
    
    assert items == []
    
@pytest.mark.parametrize("status", ["open", "completed", "cancelled"])
def test_add_access_review_item_rejects_non_draft_campaign(app, status):
    """
    Verify that snapshots cannot be added to a campaign outside draft status.
    """

    review = create_access_review(
        name="September review",
        created_by_user_id="creator-123",
        reviewer_user_id="reviewer-456",
    )

    review.status = status
    db.session.flush()

    with pytest.raises(ValueError, match="access_review_not_draft"):
        add_access_review_item(
            review_id=review.id,
            user_id="user-123",
            username="alice",
            client_name="employee-portal",
            role_id="finance-role-id",
            role_name="finance-data-viewer",
        )

    assert review.items == []


def test_add_access_review_item_rejects_missing_campaign(app):
    """
    Verify that a snapshot cannot be added to a nonexistent campaign.
    """

    with pytest.raises(ValueError, match="access_review_not_found"):
        add_access_review_item(
            review_id=999999,
            user_id="user-123",
            username="alice",
            client_name="employee-portal",
            role_id="finance-role-id",
            role_name="finance-data-viewer",
        )


def test_add_access_review_item_does_not_commit(app):
    """Verify that rolling back removes a new item but preserves its campaign."""
    review = create_access_review(
        name="September review",
        created_by_user_id="creator-123",
        reviewer_user_id="reviewer-456",
    )
    db.session.commit()
    review_id = review.id

    item = add_access_review_item(
        review_id=review_id,
        user_id="user-123",
        username="alice",
        client_name="employee-portal",
        role_id="finance-role-id",
        role_name="finance-data-viewer",
    )
    item_id = item.id

    db.session.rollback()

    assert db.session.get(AccessReviewItem, item_id) is None
    assert db.session.get(AccessReview, review_id) is not None


def test_open_access_review_opens_draft_campaign(app):
    """
    Verify that a draft campaign containing a snapshot can be opened.
    """

    review = create_access_review(
        name="September review",
        created_by_user_id="creator-123",
        reviewer_user_id="reviewer-456",
    )
    add_access_review_item(
        review_id=review.id,
        user_id="user-123",
        username="alice",
        client_name="employee-portal",
        role_id="finance-role-id",
        role_name="finance-data-viewer",
    )

    opened_review = open_access_review(review.id)

    assert opened_review.id == review.id
    assert opened_review.status == "open"


def test_open_access_review_rejects_missing_campaign(app):
    """
    Verify that a nonexistent campaign cannot be opened.
    """

    with pytest.raises(ValueError, match="access_review_not_found"):
        open_access_review(999999)


def test_open_access_review_rejects_empty_campaign(app):
    """Verify that an empty campaign remains draft when opening is rejected."""
    review = create_access_review(
        name="Empty review",
        created_by_user_id="creator-123",
        reviewer_user_id="reviewer-456",
    )

    with pytest.raises(ValueError, match="access_review_empty"):
        open_access_review(review.id)

    assert review.status == "draft"


@pytest.mark.parametrize("status", ["open", "completed", "cancelled"])
def test_open_access_review_rejects_non_draft_campaign(app, status):
    """
    Verify that opening is rejected for campaigns outside draft status.
    """
    review = create_access_review(
        name="September review",
        created_by_user_id="creator-123",
        reviewer_user_id="reviewer-456",
    )
    review.status = status
    db.session.flush()

    with pytest.raises(ValueError, match="access_review_not_draft"):
        open_access_review(review.id)

    assert review.status == status


def test_open_access_review_does_not_commit(app):
    """Verify that rolling back restores an opened campaign to draft status."""
    review = create_access_review(
        name="September review",
        created_by_user_id="creator-123",
        reviewer_user_id="reviewer-456",
    )
    add_access_review_item(
        review_id=review.id,
        user_id="user-123",
        username="alice",
        client_name="employee-portal",
        role_id="finance-role-id",
        role_name="finance-data-viewer",
    )
    db.session.commit()
    review_id = review.id

    open_access_review(review_id)
    db.session.rollback()

    persisted_review = db.session.get(AccessReview, review_id)

    assert persisted_review is not None
    assert persisted_review.status == "draft"


def test_cancel_access_review_cancels_draft_campaign(app):
    """
    Verify that a draft campaign can be cancelled.
    """
    campaign_test = create_access_review("test campaign", "creator-123", "reviewer-123")

    result = cancel_access_review(campaign_test.id)

    assert result.status == "cancelled"


def test_cancel_access_review_preserves_items(app):
    """
    Verify that cancelling an open campaign preserves its captured access items.
    """
    campaign_test = create_access_review("test campaign", "creator-123", "reviewer-123")

    item = add_access_review_item(
        review_id=campaign_test.id,
        user_id="user-123",
        username="alice",
        client_name="employee-portal",
        role_id="finance-role-id",
        role_name="finance-data-viewer",
    )
    open_access_review(campaign_test.id)
    result = cancel_access_review(campaign_test.id)

    assert result.status == "cancelled"
    assert item in campaign_test.items


def test_cancel_access_review_rejects_completed_campaign(app):
    """
    Verify that a completed campaign cannot be cancelled.
    """

    campaign_test = create_access_review("test campaign", "creator-123", "reviewer-123")
    campaign_test.status = "completed"
    db.session.flush()

    with pytest.raises(ValueError, match="access_review_not_cancellable"):
        cancel_access_review(campaign_test.id)

    assert campaign_test.status == "completed"


def test_cancel_access_review_does_not_commit(app):
    """
    Verify that rolling back cancellation restores the campaign's draft status.
    """

    campaign_test = create_access_review("test campaign", "creator-123", "reviewer-123")
    db.session.commit()
    review_id = campaign_test.id

    cancel_access_review(review_id)
    db.session.rollback()

    campaign_test_rollbacked = db.session.get(AccessReview, review_id)

    assert campaign_test_rollbacked is not None
    assert campaign_test_rollbacked.status == "draft"


def test_get_access_reviews_for_reviewer_excludes_other_reviewers(app):
    """
    Verify that a reviewer receives only campaigns assigned to them.
    """

    first_review = create_access_review("test campaign 1", "user-123", "reviewer-123")
    second_review = create_access_review("test campaign 2", "user-456", "reviewer-456")

    result = get_access_reviews_for_reviewer("reviewer-123")

    assert result == [first_review]


def test_get_access_reviews_for_reviewer_returns_newest_first(app):
    """
    Verify that assigned campaigns are returned newest first.
    """
    older_campaign = create_access_review("test campaign 1", "user-123", "reviewer-123")
    newer_campaign = create_access_review("test campaign 2", "user-456", "reviewer-123")

    older_campaign.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    newer_campaign.created_at = datetime(2026, 1, 2, tzinfo=timezone.utc)
    db.session.flush()

    result = get_access_reviews_for_reviewer("reviewer-123")

    assert result == [newer_campaign, older_campaign]


def test_get_access_reviews_for_reviewer_returns_empty_list(app):
    """
    Verify that a reviewer with no assigned campaigns receives an empty list.
    """

    campaign = create_access_review("test campaign", "user-123", "reviewer-123")
    db.session.flush()

    result = get_access_reviews_for_reviewer("reviewer-456")

    assert result == []


def test_get_access_review_for_reviewer_returns_assigned_campaign(app):
    """
    Verify that the assigned reviewer can retrieve a specific campaign.
    """

    campaign = create_access_review("test campaign", "user-123", "reviewer-123")

    result = get_access_review_for_reviewer(campaign.id, "reviewer-123")

    assert result == campaign


def test_get_access_review_for_reviewer_rejects_other_reviewer(app):
    """
    Verify that a reviewer cannot retrieve another reviewer's campaign.
    """

    campaign = create_access_review("test campaign", "user-123", "reviewer-123")

    with pytest.raises(ValueError, match="access_review_not_found"):
        get_access_review_for_reviewer(campaign.id, "reviewer-456")


def test_get_access_review_for_reviewer_rejects_missing_campaign(app):
    """
    Verify that retrieving a nonexistent campaign raises the not-found error.
    """
    with pytest.raises(ValueError, match="access_review_not_found"):
        get_access_review_for_reviewer(999999, "reviewer-456")


def test_get_access_review_for_manager_returns_owned_campaign(app):
    """
    Verify that a manager can retrieve a campaign they created.
    """
    campaign = create_access_review(
        "Manager campaign",
        "manager-123",
        "reviewer-123",
    )

    result = get_access_review_for_manager(campaign.id, "manager-123")

    assert result == campaign


def test_get_access_review_for_manager_rejects_other_manager(app):
    """
    Verify that a manager cannot retrieve another manager's campaign.
    """
    campaign = create_access_review(
        "Private campaign",
        "manager-123",
        "reviewer-123",
    )

    with pytest.raises(
        ValueError,
        match="access_review_not_found",
    ):
        get_access_review_for_manager(
            campaign.id,
            "manager-456",
        )


def test_get_access_review_for_manager_rejects_missing_campaign(app):
    """
    Verify that a nonexistent campaign returns the same not-found error.
    """
    with pytest.raises(
        ValueError,
        match="access_review_not_found",
    ):
        get_access_review_for_manager(
            999999,
            "manager-123",
        )


def test_get_access_reviews_for_manager_excludes_other_managers(app):
    """
    Verify that a manager receives only campaigns they created.
    """

    first_review = create_access_review(
        "test campaign 1", "manager-123", "reviewer-123"
    )
    second_review = create_access_review(
        "test campaign 2", "manager-456", "reviewer-456"
    )

    result = get_access_reviews_for_manager("manager-123")

    assert result == [first_review]


def test_get_access_reviews_for_manager_returns_newest_first(app):
    """
    Verify that a manager's campaigns are returned newest first.
    """

    older_campaign = create_access_review(
        "test campaign 1", "manager-123", "reviewer-123"
    )
    newer_campaign = create_access_review(
        "test campaign 2", "manager-123", "reviewer-123"
    )

    older_campaign.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    newer_campaign.created_at = datetime(2026, 1, 2, tzinfo=timezone.utc)
    db.session.flush()

    result = get_access_reviews_for_manager("manager-123")

    assert result == [newer_campaign, older_campaign]


def test_get_access_reviews_for_manager_returns_empty_list(app):
    """
    Verify that a manager with no created campaigns receives an empty list.
    """

    create_access_review("test campaign", "manager-123", "reviewer-123")
    db.session.flush()

    result = get_access_reviews_for_manager("manager-456")

    assert result == []


def test_validate_access_review_reviewer_accepts_eligible_user(monkeypatch):
    """
    Verify that an enabled user with reviewer access is accepted.
    """
    reviewer = {
        "id": "reviewer-123",
        "username": "e1005",
        "enabled": True,
    }

    fake_get_user = Mock(return_value=reviewer)
    fake_get_roles = Mock(return_value=[{"name": "access-reviewer"}])

    monkeypatch.setattr(access_review_service, "get_user", fake_get_user)
    monkeypatch.setattr(
        access_review_service,
        "get_effective_client_roles",
        fake_get_roles,
    )

    result = validate_access_review_reviewer(
        reviewer_user_id=" reviewer-123 ",
        admin_api_url="https://keycloak.test/admin",
        token_url="https://keycloak.test/token",
        client_id="iam-governance-service",
        client_secret="test-secret",
    )

    assert result == reviewer

    fake_get_user.assert_called_once_with(
        admin_api_url="https://keycloak.test/admin",
        token_url="https://keycloak.test/token",
        client_id="iam-governance-service",
        client_secret="test-secret",
        user_id="reviewer-123",
    )

    fake_get_roles.assert_called_once_with(
        admin_api_url="https://keycloak.test/admin",
        token_url="https://keycloak.test/token",
        client_id="iam-governance-service",
        client_secret="test-secret",
        user_id="reviewer-123",
        target_client_name="iam-admin-portal",
    )


def test_validate_access_review_reviewer_rejects_disabled_user(monkeypatch):
    """
    Verify that a disabled reviewer is rejected before their roles are retrieved.
    """

    fake_get_user = Mock(return_value={"enabled": False})
    fake_get_roles = Mock()

    monkeypatch.setattr(access_review_service, "get_user", fake_get_user)

    monkeypatch.setattr(
        access_review_service,
        "get_effective_client_roles",
        fake_get_roles,
    )

    with pytest.raises(ValueError, match="reviewer_not_enabled"):
        validate_access_review_reviewer(
            reviewer_user_id=" reviewer-123 ",
            admin_api_url="https://keycloak.test/admin",
            token_url="https://keycloak.test/token",
            client_id="iam-governance-service",
            client_secret="test-secret",
        )

    fake_get_roles.assert_not_called()


def test_validate_access_review_reviewer_rejects_missing_roles(monkeypatch):
    """
    Verify that an enabled user without reviewer access is rejected.
    """

    fake_get_user = Mock(return_value={"enabled": True})
    fake_get_roles = Mock(return_value=[{"name": "identity-viewer"}])

    monkeypatch.setattr(access_review_service, "get_user", fake_get_user)

    monkeypatch.setattr(
        access_review_service,
        "get_effective_client_roles",
        fake_get_roles,
    )

    with pytest.raises(ValueError, match="reviewer_missing_required_role"):
        validate_access_review_reviewer(
            reviewer_user_id=" reviewer-123 ",
            admin_api_url="https://keycloak.test/admin",
            token_url="https://keycloak.test/token",
            client_id="iam-governance-service",
            client_secret="test-secret",
        )

    fake_get_roles.assert_called_once()


def test_validate_access_review_reviewer_propagates_lookup_failure(monkeypatch):
    """
    Verify that a failed user lookup propagates without retrieving roles.
    """

    fake_get_user = Mock(side_effect=KeycloakAdminAPIError("User retrieval failed"))

    fake_get_roles = Mock()

    monkeypatch.setattr(access_review_service, "get_user", fake_get_user)

    monkeypatch.setattr(
        access_review_service,
        "get_effective_client_roles",
        fake_get_roles,
    )

    with pytest.raises(KeycloakAdminAPIError, match="User retrieval failed"):
        validate_access_review_reviewer(
            reviewer_user_id="reviewer-123",
            admin_api_url="https://keycloak.test/admin",
            token_url="https://keycloak.test/token",
            client_id="iam-governance-service",
            client_secret="test-secret",
        )

    fake_get_roles.assert_not_called()


def test_validate_access_review_reviewer_propagates_role_lookup_failure(monkeypatch):
    """
    Verify that a failed role lookup prevents reviewer validation from succeeding.
    """

    fake_get_user = Mock(return_value={"enabled": True})

    fake_get_roles = Mock(side_effect=KeycloakAdminAPIError("Role retrieval failed"))

    monkeypatch.setattr(access_review_service, "get_user", fake_get_user)

    monkeypatch.setattr(
        access_review_service,
        "get_effective_client_roles",
        fake_get_roles,
    )

    with pytest.raises(KeycloakAdminAPIError, match="Role retrieval failed"):
        validate_access_review_reviewer(
            reviewer_user_id="reviewer-123",
            admin_api_url="https://keycloak.test/admin",
            token_url="https://keycloak.test/token",
            client_id="iam-governance-service",
            client_secret="test-secret",
        )

    fake_get_roles.assert_called_once()


def test_populate_access_review_captures_managed_direct_role(monkeypatch, app):
    """
    Verify that a managed direct role is captured in a manager-owned draft campaign.
    """

    campaign = create_access_review("test campaign", "manager-123", "reviewer-456")

    managed_role = ManagedRole(
        client_name="employee-portal", role_name="finance-data-viewer", enabled=True
    )

    db.session.add(managed_role)
    db.session.flush()

    fake_get_user = Mock(return_value={"id": "user-123", "username": "alice"})
    fake_get_direct_client_role = fake_get_direct_client_role = Mock(
        return_value=[
            {
                "id": "finance-role-id",
                "name": "finance-data-viewer",
            }
        ]
    )

    monkeypatch.setattr(access_review_service, "get_user", fake_get_user)

    monkeypatch.setattr(
        access_review_service, "get_direct_client_roles", fake_get_direct_client_role
    )

    created_items = access_review_service.populate_access_review_from_identity(
        review_id=campaign.id,
        manager_user_id="manager-123",
        user_id="user-123",
        admin_api_url="https://keycloak.test/admin",
        token_url="https://keycloak.test/token",
        client_id="iam-governance-service",
        client_secret="test-secret",
    )

    assert len(created_items) == 1

    item = created_items[0]

    assert item.id is not None
    assert item.review_id == campaign.id
    assert item.user_id == "user-123"
    assert item.username == "alice"
    assert item.client_name == "employee-portal"
    assert item.role_id == "finance-role-id"
    assert item.role_name == "finance-data-viewer"


def test_populate_access_review_skips_existing_items(app, monkeypatch):
    """
    Verify that repeated population does not duplicate captured access items.
    """
    campaign = create_access_review(
        "test campaign",
        "manager-123",
        "reviewer-456",
    )

    managed_role = ManagedRole(
        client_name="employee-portal",
        role_name="finance-data-viewer",
        enabled=True,
    )
    db.session.add(managed_role)
    db.session.flush()

    monkeypatch.setattr(
        access_review_service,
        "get_user",
        Mock(
            return_value={
                "id": "user-123",
                "username": "alice",
            }
        ),
    )

    monkeypatch.setattr(
        access_review_service,
        "get_direct_client_roles",
        Mock(
            return_value=[
                {
                    "id": "finance-role-id",
                    "name": "finance-data-viewer",
                }
            ]
        ),
    )

    arguments = {
        "review_id": campaign.id,
        "manager_user_id": "manager-123",
        "user_id": "user-123",
        "admin_api_url": "https://keycloak.test/admin",
        "token_url": "https://keycloak.test/token",
        "client_id": "iam-governance-service",
        "client_secret": "test-secret",
    }

    first_items = access_review_service.populate_access_review_from_identity(
        **arguments
    )
    second_items = access_review_service.populate_access_review_from_identity(
        **arguments
    )

    assert len(first_items) == 1
    assert second_items == []

    saved_items = (
        db.session.execute(
            db.select(AccessReviewItem).where(
                AccessReviewItem.review_id == campaign.id,
            )
        )
        .scalars()
        .all()
    )

    assert len(saved_items) == 1
    assert saved_items[0].id == first_items[0].id


def test_populate_access_review_rejects_other_manager(app, monkeypatch):
    """
    Verify that another manager cannot populate a campaign or trigger Keycloak lookups.
    """
    campaign = create_access_review(
        "test campaign",
        "manager-123",
        "reviewer-456",
    )

    fake_get_user = Mock()
    fake_get_roles = Mock()

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

    with pytest.raises(ValueError, match="access_review_not_found"):
        access_review_service.populate_access_review_from_identity(
            review_id=campaign.id,
            manager_user_id="other-manager",
            user_id="user-123",
            admin_api_url="https://keycloak.test/admin",
            token_url="https://keycloak.test/token",
            client_id="iam-governance-service",
            client_secret="test-secret",
        )

    fake_get_user.assert_not_called()
    fake_get_roles.assert_not_called()

    saved_items = (
        db.session.execute(
            db.select(AccessReviewItem).where(
                AccessReviewItem.review_id == campaign.id,
            )
        )
        .scalars()
        .all()
    )

    assert saved_items == []


@pytest.mark.parametrize("status", ["open", "completed", "cancelled"])
def test_populate_access_review_rejects_non_draft_campaign(app, monkeypatch, status):
    """
    Verify that non-draft campaigns reject population before Keycloak lookups.
    """
    campaign = create_access_review(
        "test campaign",
        "manager-123",
        "reviewer-456",
    )

    campaign.status = status
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
        "get_direct_client_roles",
        fake_get_roles,
    )
    with pytest.raises(ValueError, match="access_review_not_draft"):
        result = access_review_service.populate_access_review_from_identity(
            review_id=campaign.id,
            manager_user_id="manager-123",
            user_id="user-123",
            admin_api_url="https://keycloak.test/admin",
            token_url="https://keycloak.test/token",
            client_id="iam-governance-service",
            client_secret="test-secret",
        )

        fake_get_user.assert_not_called()
        fake_get_roles.assert_not_called()
        assert (
            db.session.execute(
                db.select(AccessReviewItem).where(
                    AccessReviewItem.review_id == campaign.id,
                )
            )
            .scalars()
            .all()
            == []
        )


def test_populate_access_review_skips_unmanaged_roles(app, monkeypatch):
    """
    Verify that population captures managed roles and skips unmanaged direct roles.
    """
    campaign = create_access_review(
        "test campaign",
        "manager-123",
        "reviewer-456",
    )

    managed_role = ManagedRole(
        client_name="employee-portal",
        role_name="finance-data-viewer",
        enabled=True,
    )
    db.session.add(managed_role)
    db.session.flush()

    monkeypatch.setattr(
        access_review_service,
        "get_user",
        Mock(
            return_value={
                "id": "user-123",
                "username": "alice",
            }
        ),
    )

    monkeypatch.setattr(
        access_review_service,
        "get_direct_client_roles",
        Mock(
            return_value=[
                {
                    "id": "portal-role-id",
                    "name": "portal-user",
                },
                {
                    "id": "finance-role-id",
                    "name": "finance-data-viewer",
                },
            ]
        ),
    )

    created_items = access_review_service.populate_access_review_from_identity(
        review_id=campaign.id,
        manager_user_id="manager-123",
        user_id="user-123",
        admin_api_url="https://keycloak.test/admin",
        token_url="https://keycloak.test/token",
        client_id="iam-governance-service",
        client_secret="test-secret",
    )

    assert len(created_items) == 1
    assert created_items[0].role_name == "finance-data-viewer"
    assert created_items[0].role_id == "finance-role-id"

    saved_items = (
        db.session.execute(
            db.select(AccessReviewItem).where(
                AccessReviewItem.review_id == campaign.id,
            )
        )
        .scalars()
        .all()
    )

    assert len(saved_items) == 1
    assert saved_items[0].id == created_items[0].id
    assert saved_items[0].role_name == "finance-data-viewer"


def test_populate_access_review_does_not_commit(app, monkeypatch):
    """
    Verify that captured access items can be rolled back while the campaign remains saved.
    """
    campaign = create_access_review(
        "test campaign",
        "manager-123",
        "reviewer-456",
    )

    managed_role = ManagedRole(
        client_name="employee-portal",
        role_name="finance-data-viewer",
        enabled=True,
    )
    db.session.add(managed_role)
    db.session.commit()

    campaign_id = campaign.id

    monkeypatch.setattr(
        access_review_service,
        "get_user",
        Mock(
            return_value={
                "id": "user-123",
                "username": "alice",
            }
        ),
    )

    monkeypatch.setattr(
        access_review_service,
        "get_direct_client_roles",
        Mock(
            return_value=[
                {
                    "id": "finance-role-id",
                    "name": "finance-data-viewer",
                }
            ]
        ),
    )

    created_items = access_review_service.populate_access_review_from_identity(
        review_id=campaign_id,
        manager_user_id="manager-123",
        user_id="user-123",
        admin_api_url="https://keycloak.test/admin",
        token_url="https://keycloak.test/token",
        client_id="iam-governance-service",
        client_secret="test-secret",
    )

    assert len(created_items) == 1
    assert created_items[0].id is not None

    db.session.rollback()

    saved_campaign = db.session.get(AccessReview, campaign_id)
    assert saved_campaign is not None
    assert saved_campaign.status == "draft"

    saved_items = (
        db.session.execute(
            db.select(AccessReviewItem).where(
                AccessReviewItem.review_id == campaign_id,
            )
        )
        .scalars()
        .all()
    )

    assert saved_items == []
