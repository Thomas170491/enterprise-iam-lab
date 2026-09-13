import pytest
from datetime import datetime,timezone
from services.access_review_service import create_access_review
from extensions import db
from models import AccessReview

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