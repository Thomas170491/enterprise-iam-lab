from datetime import datetime 
from models import AccessReview
from extensions import db 

def create_access_review(
    name : str, 
    created_by_user_id : str,
    reviewer_user_id : str,
    due_at : str | None = None  
):
    """
    Create a draft access review campaign with an assigned reviewer
    and optional due date.
    Flush the campaign without committing; the caller owns the transaction.
    """
    
    if not isinstance(name, str):
        raise ValueError("invalid_review_name")
    
    name = name.strip()
    
    if not name or len(name) > 200:
        raise ValueError("invalid_review_name")

    
    if not isinstance(created_by_user_id,str) :
        raise ValueError("invalid_creator_user_id")
    
    if not isinstance(reviewer_user_id,str):
        raise ValueError("invalid_reviewer_user_id")
    
    created_by_user_id = created_by_user_id.strip()
    reviewer_user_id = reviewer_user_id.strip()
    
    if not created_by_user_id or len(created_by_user_id) > 255 :
        raise ValueError("invalid_creator_user_id")
    
    if not reviewer_user_id or len(reviewer_user_id) > 255 :
        raise ValueError("invalid_reviewer_user_id")   
    
    if due_at is not None : 
        
        if not isinstance(due_at,datetime) :
            raise ValueError("invalid_due_at")
        
        if due_at.tzinfo is None or due_at.utcoffset() is None :
            raise ValueError("invalid_due_at")
    
    access_review = AccessReview(
        name = name,
        created_by_user_id  = created_by_user_id,
        reviewer_user_id = reviewer_user_id,
        due_at = due_at,
        status = "draft",
    )
    db.session.add(access_review)
    db.session.flush()
    
    return access_review
        
                
    
    