from datetime import datetime

from extensions import db
from models import AccessReview, AccessReviewItem
from services.audit_service import record_audit_event
from services.keycloak_admin_service import get_effective_client_roles, get_user

def _validate_required_string(value, field_name, max_length):
    """Return a trimmed required string or raise a field-specific ValueError."""
    if not isinstance(value, str):
        raise ValueError(f"invalid_{field_name}")

    value = value.strip()

    if not value or len(value) > max_length:
        raise ValueError(f"invalid_{field_name}")

    return value


def create_access_review(
    name: str,
    created_by_user_id: str,
    reviewer_user_id: str,
    due_at: datetime | None = None,
) -> AccessReview:
    """
    Create a draft access review campaign with an assigned reviewer.

    Validate and trim required strings. An optional due date must
    be a timezone-aware datetime.

    Flush the campaign without committing; the caller owns the transaction.
    """
    name = _validate_required_string(name, "review_name", 200)
    created_by_user_id = _validate_required_string(
        created_by_user_id, "creator_user_id", 255
    )
    reviewer_user_id = _validate_required_string(
        reviewer_user_id, "reviewer_user_id", 255
    )

    if due_at is not None:
        if not isinstance(due_at, datetime):
            raise ValueError("invalid_due_at")

        if due_at.tzinfo is None or due_at.utcoffset() is None:
            raise ValueError("invalid_due_at")

    access_review = AccessReview(
        name=name,
        created_by_user_id=created_by_user_id,
        reviewer_user_id=reviewer_user_id,
        due_at=due_at,
        status="draft",
    )

    db.session.add(access_review)
    db.session.flush()

    return access_review


def add_access_review_item(
    review_id: int,
    user_id: str,
    username: str,
    client_name: str,
    role_id: str,
    role_name: str,
) -> AccessReviewItem:
    """
    Add an identity-role snapshot to an existing draft review campaign.

    Validate and trim the required identity and role details.

    Flush the item without committing; the caller owns the transaction.
    """
    campaign = db.session.get(AccessReview, review_id)

    if campaign is None:
        raise ValueError("access_review_not_found")

    if campaign.status != "draft":
        raise ValueError("access_review_not_draft")

    user_id = _validate_required_string(user_id, "user_id", 255)
    username = _validate_required_string(username, "username", 255)
    client_name = _validate_required_string(client_name, "client_name", 100)
    role_id = _validate_required_string(role_id, "role_id", 255)
    role_name = _validate_required_string(role_name, "role_name", 100)

    item = AccessReviewItem(
        review=campaign,
        user_id=user_id,
        username=username,
        client_name=client_name,
        role_id=role_id,
        role_name=role_name,
    )

    db.session.add(item)
    db.session.flush()

    return item

def open_access_review(review_id : int) -> AccessReview :
    """
    Open an existing draft access review campaign containing at least one item.

    Flush the status change without committing; the caller owns the transaction.
    """
    
    campaign = db.session.get(AccessReview, review_id)
    
    if campaign is None :
        raise ValueError("access_review_not_found")
    
    if campaign.status != "draft" :
        raise ValueError("access_review_not_draft")
    
    if not campaign.items :
        raise ValueError("access_review_empty")
    
    campaign.status = "open"
    db.session.flush()
    
    return campaign 

def cancel_access_review(review_id : int) -> AccessReview :
    """
    Cancel a draft or open access review campaign while preserving its items.

    Flush the status change without committing; the caller owns the transaction.
    """
    
    campaign = db.session.get(AccessReview, review_id)
    
    if campaign is None :
        raise ValueError("access_review_not_found")
    
    if campaign.status not in ("draft", "open" ) :
        raise ValueError("access_review_not_cancellable")
    
    campaign.status ="cancelled"
    
    db.session.flush()
    
    return campaign

def get_access_reviews_for_reviewer(reviewer_user_id : str) -> list[AccessReview]:
    """
    Return campaigns assigned to the specified reviewer, newest first.

    Include all campaign statuses without modifying the database.
    """
    
    reviewer_user_id = _validate_required_string(reviewer_user_id,"reviewer_user_id",255)
    
    return db.session.execute(
        db.select(AccessReview)
        .where(AccessReview.reviewer_user_id == reviewer_user_id)
        .order_by(AccessReview.created_at.desc(), AccessReview.id.desc())       
        
    ).scalars().all()
    
def get_access_review_for_reviewer(review_id : int, reviewer_user_id : str) -> AccessReview :
    """
    Return a campaign only when it is assigned to the specified reviewer.

    Raise the same not-found error for missing and unassigned campaigns.
    """
    
    reviewer_user_id = _validate_required_string(reviewer_user_id,"reviewer_user_id",255,)
    
    campaign = db.session.execute(
        db.select(AccessReview)
        .where(AccessReview.id == review_id , AccessReview.reviewer_user_id == reviewer_user_id)
    ).scalar_one_or_none()
        
    if campaign is None :
        raise ValueError("access_review_not_found")
    
    return campaign
    
    
def create_access_review_with_audit(
    name : str,
    created_by_user_id :str,
    actor_username : str,
    reviewer_user_id :str,
    admin_api_url :str,
    token_url : str,
    client_id :str,
    client_secret : str,
    due_at : datetime | None = None
) -> AccessReview:
    """
    Validate reviewer eligibility, then create a draft campaign and its audit event.

    Commit both records together, rolling back on failure.
    """
    
    try:
        validate_access_review_reviewer(
            reviewer_user_id= reviewer_user_id,
            admin_api_url=admin_api_url,
            token_url=token_url,
            client_id=client_id,
            client_secret=client_secret,     
        )
        
        review = create_access_review(name, created_by_user_id,reviewer_user_id,due_at)
        
        record_audit_event(
            actor_user_id=review.created_by_user_id,
            actor_username=actor_username,
            action="access_review.create",
            target_type="access_review",
            target_id=str(review.id),
            target_name=review.name,
            outcome="success",
            details={
                "source": "governance-portal",
                "reviewer_user_id": review.reviewer_user_id,
                "status": review.status,
            },
            commit=False,
        )
        db.session.commit()
        
    except Exception:
        db.session.rollback()
        raise
    
    return review

def get_access_review_for_manager(review_id : int, manager_user_id : str) -> AccessReview :
    """
    Return an access review campaign only when it was created by
    the specified access review manager.

    Raise the same not-found error for missing and unauthorized
    campaigns to avoid exposing campaign existence.
    """

    manager_user_id = _validate_required_string(manager_user_id,"manager_user_id",255,)

    campaign = db.session.execute(
        db.select(AccessReview).where(
            AccessReview.id == review_id,
            AccessReview.created_by_user_id == manager_user_id,
        )
    ).scalar_one_or_none()

    if campaign is None:
        raise ValueError("access_review_not_found")

    return campaign

def get_access_reviews_for_manager(manager_user_id: str) -> list[AccessReview]:
    """
    Return access review campaigns created by the specified manager, newest first.

    Include all campaign statuses without modifying the database.
    """
    
    manager_user_id=_validate_required_string(manager_user_id,"manager_user_id",255)
    
    return db.session.execute(
        db.select(AccessReview)
        .where(AccessReview.created_by_user_id == manager_user_id)
        .order_by(AccessReview.created_at.desc(), AccessReview.id.desc())  
    ).scalars().all()
    
def validate_access_review_reviewer(
    reviewer_user_id: str,
    admin_api_url: str,
    token_url: str,
    client_id: str,
    client_secret: str,
)-> dict :
    """
    Verify that the assigned reviewer exists, is enabled, and has reviewer access.
    """
    
    reviewer_user_id = _validate_required_string(reviewer_user_id,"reviewer_user_id", 255)
    
    reviewer = get_user(
        admin_api_url=admin_api_url,
        token_url=token_url,
        client_id=client_id,
        client_secret=client_secret,
        user_id= reviewer_user_id
    )
    
    if  reviewer.get("enabled") is not True:
        raise ValueError("reviewer_not_enabled")
    
    reviewer_roles = get_effective_client_roles(
        admin_api_url=admin_api_url,
        token_url=token_url,
        client_id=client_id,
        client_secret=client_secret,
        user_id=reviewer_user_id,
        target_client_name="iam-admin-portal",
    )
    
    if not any(role.get("name")== "access-reviewer" for role in reviewer_roles) : 
        raise ValueError("reviewer_missing_required_role")
    
    return reviewer