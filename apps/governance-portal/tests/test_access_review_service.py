import pytest
from datetime import datetime,timezone
from services.access_review_service import (add_access_review_item,
                                            create_access_review, get_access_review_for_reviewer, 
                                            open_access_review,
                                            cancel_access_review,
                                            get_access_reviews_for_reviewer
)
from extensions import db
from models import AccessReview,AccessReviewItem

def test_create_access_review(app):
    """
    Verify that creating an access review trims its inputs and returns a draft campaign.
    """    
    
    review = create_access_review(" name string ", " created by Thomas ", " reviewer Agnes ")
    
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
        create_access_review(" ","creator-123","reviewer-123")
        
def test_create_access_review_rejects_naive_due_at(app):
    """
    Verify that a due date without timezone information is rejected.
    """
    
    date = datetime(2026,12,1)
    
    with pytest.raises(ValueError, match="invalid_due_at"):
        create_access_review("name", "id1","id2", date)

def test_create_access_review_preserves_aware_due_at(app):
    """
    Verify that a timezone-aware due date is preserved when creating a campaign.
    """
    
    date = datetime(2026, 12, 1, tzinfo=timezone.utc)
    
    result=create_access_review("name", "id1","id2", date)
    
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
    
    assert db.session.get(AccessReview,review_id) is None
    
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
    campaign_test= create_access_review("test campaign", "creator-123", "reviewer-123")
    
    result = cancel_access_review(campaign_test.id)
    
    assert result.status == "cancelled"
    
    
def test_cancel_access_review_preserves_items(app):
    """
    Verify that cancelling an open campaign preserves its captured access items.
    """
    campaign_test= create_access_review("test campaign", "creator-123", "reviewer-123")
    
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
    
    campaign_test= create_access_review("test campaign", "creator-123", "reviewer-123")
    campaign_test.status = "completed"
    db.session.flush()
    
    with pytest.raises(ValueError, match= "access_review_not_cancellable"):
        cancel_access_review(campaign_test.id)
        
    assert campaign_test.status =="completed"
    
def test_cancel_access_review_does_not_commit(app):
    """
    Verify that rolling back cancellation restores the campaign's draft status.
    """
    
    campaign_test= create_access_review("test campaign", "creator-123", "reviewer-123")
    db.session.commit()
    review_id = campaign_test.id
    
    
    
    cancel_access_review(review_id)
    db.session.rollback()
    
    campaign_test_rollbacked =db.session.get(AccessReview, review_id)
     
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
    newer_campaign= create_access_review("test campaign 2", "user-456", "reviewer-123")
    
    older_campaign.created_at = datetime(2026,1,1,tzinfo=timezone.utc)
    newer_campaign.created_at = datetime(2026,1,2,tzinfo=timezone.utc)
    db.session.flush()
    
    result =get_access_reviews_for_reviewer("reviewer-123")
    
    assert result == [newer_campaign,older_campaign]
    
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
    
    result = get_access_review_for_reviewer(campaign.id,"reviewer-123")
    
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

