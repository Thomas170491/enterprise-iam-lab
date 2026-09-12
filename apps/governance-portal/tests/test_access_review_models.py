import pytest

from extensions import db
from models import AccessReview,AccessReviewItem
from sqlalchemy.exc import IntegrityError

def test_access_review_defaults_to_draft(app):
    """
    Verify that a new access review defaults to draft and receives creation timestamps.
    """
    
    access_review = AccessReview(
        name = "test_review",
        created_by_user_id = "testuser1",
        reviewer_user_id  = "testuser2"
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
        name = "test_review",
        created_by_user_id = "testuser1",
        reviewer_user_id  = "testuser2"
    )
    
    access_review_item = AccessReviewItem(
        review = access_review,
        user_id = "testuser31",
        username = "testuser",
        client_name = "employee-portal",
        role_name = "testrole",
        role_id="fake-id"
    )
    
    db.session.add_all([access_review,access_review_item])
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
        name = "test_review",
        created_by_user_id = "testuser1",
        reviewer_user_id  = "testuser2",
        status = "invalid"
    )
    
    db.session.add(access_review)
    
    with pytest.raises(IntegrityError) :
        db.session.flush()
    
    db.session.rollback()
    
def test_access_review_rejects_duplicate_items(app):
    """
    Verify that a campaign cannot contain duplicate entries for the same identity, client, and role.
    """
    
    access_review = AccessReview(
        name = "test_review",
        created_by_user_id = "testuser1",
        reviewer_user_id  = "testuser2"
    )
    
    access_review_item = AccessReviewItem(
        review = access_review,
        user_id = "testuser31",
        username = "testuser",
        client_name = "employee-portal",
        role_name = "testrole",
        role_id="fake-id"
    )
    
    db.session.add_all([access_review,access_review_item])
    db.session.flush()
    
    access_review_item2 = AccessReviewItem(
        review = access_review,
        user_id = "testuser31",
        username = "testuser",
        client_name = "employee-portal",
        role_name = "testrole",
        role_id="fake-id"
    )
    
    db.session.add(access_review_item2)

    with pytest.raises(IntegrityError):
        db.session.flush()
    
    db.session.rollback()