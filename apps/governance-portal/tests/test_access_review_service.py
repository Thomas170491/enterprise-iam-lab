import pytest
from datetime import datetime,timezone
from services.access_review_service import add_access_review_item, create_access_review
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