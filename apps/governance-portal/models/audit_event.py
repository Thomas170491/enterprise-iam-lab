from extensions import db

class AuditEvent(db.Model):
    __tablename__ = "audit_event"

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True), 
                           nullable=False, 
                           server_default=db.func.now(),
                           index=True
    )

    # Keycloak user ID / OIDC subject of the actor.
    actor_user_id = db.Column(
        db.String(255),
        nullable=False,
        index=True,
    )

    # Human-readable snapshot at the time of the event.
    actor_username = db.Column(
        db.String(255),
        nullable=False,
    )

    # Examples:
    # identity.view
    # access.review
    # role.assign
    action = db.Column(
        db.String(100),
        nullable=False,
        index=True,
    )

    # Examples:
    # identity
    # role
    # access_request
    target_type = db.Column(
        db.String(100),
        nullable=False,
    )

    # Usually the immutable Keycloak ID of the target.
    target_id = db.Column(
        db.String(255),
        nullable=True,
        index=True,
    )

    # Human-readable snapshot of the target.
    target_name = db.Column(
        db.String(255),
        nullable=True,
    )

    # Examples:
    # success
    # failure
    # denied
    outcome = db.Column(
        db.String(32),
        nullable=False,
    )

    # Flexible contextual information.
    details = db.Column(
        db.JSON,
        nullable=True,
    )

    def __repr__(self):
        return (
            f"<AuditEvent "
            f"id={self.id} "
            f"action={self.action!r} "
            f"outcome={self.outcome!r}>"
        )

    
