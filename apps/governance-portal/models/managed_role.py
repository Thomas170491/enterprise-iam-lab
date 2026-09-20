from extensions import db


class ManagedRole(db.Model):
    __tablename__ = "managed_roles"

    id = db.Column(db.Integer, primary_key=True)

    client_name = db.Column(db.String(100), nullable=False)

    role_name = db.Column(db.String(100), nullable=False)

    enabled = db.Column(db.Boolean, default=True, nullable=False)

    risk_level = db.Column(db.String(20), default="low", nullable=False)

    is_privileged = db.Column(db.Boolean, default=False, nullable=False)

    assignment_mode = db.Column(db.String(20), default="direct", nullable=False)

    requires_approval = db.Column(db.Boolean, default=False, nullable=False)

    requires_review = db.Column(db.Boolean, default=False, nullable=False)

    review_interval_days = db.Column(db.Integer, nullable=True)

    created_at = db.Column(
        db.DateTime(timezone=True), server_default=db.func.now(), nullable=False
    )

    updated_at = db.Column(
        db.DateTime(timezone=True),
        server_default=db.func.now(),
        onupdate=db.func.now(),
        nullable=False,
    )

    __table_args__ = (
        db.UniqueConstraint(
            "client_name", "role_name", name="uq_managed_roles_client_name_role_name"
        ),
    )
