from sqlalchemy.exc import SQLAlchemyError

from extensions import db 
from models.audit_event import AuditEvent 
from services.exceptions import AuditPersistenceError, AuditQueryError

def record_audit_event(actor_user_id, actor_username, action, target_type, target_id=None, target_name=None, outcome=None, details=None):
    """
    Records an audit event in the database.

    Args:
        actor_user_id (str): The Keycloak user ID of the actor.
        actor_username (str): The username of the actor.
        action (str): The action performed (e.g., 'identity.view').
        target_type (str): The type of the target (e.g., 'identity').
        target_id (str, optional): The ID of the target. Defaults to None.
        target_name (str, optional): The name of the target. Defaults to None.
        outcome (str, optional): The outcome of the action. Defaults to None.
        details (dict, optional): Additional details about the audit event. Defaults to None.

    Raises:
        AuditPersistenceError: If the audit event cannot be persisted to the database.
    """
    try:
        audit_event = AuditEvent(
            actor_user_id=actor_user_id,
            actor_username=actor_username,
            action=action,
            target_type=target_type,
            target_id=target_id,
            target_name=target_name,
            outcome=outcome,
            details=details,
        )
        db.session.add(audit_event)
        db.session.commit()
    except SQLAlchemyError as e:
        db.session.rollback()
        raise AuditPersistenceError(f"Failed to persist audit event: {str(e)}")

    return audit_event 

def get_recent_audit_events(limit=100):
    """
    Retrieves the most recent audit events from the database.

    Args:
        limit (int): The maximum number of audit events to retrieve. Defaults to 100.
    Events are returned newest first.
    """

    statement= db.select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(limit)

    try:
        return db.session.execute(statement).scalars().all()
    except SQLAlchemyError as e:
        db.session.rollback()
        raise AuditQueryError(f"Failed to retrieve audit events: {str(e)}")
