from extensions import db


class SoDRule(db.Model):
    __tablename__ = "sod_rules"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100), unique=True, nullable=False)

    description = db.Column(db.String(100), nullable=True)

    first_role_id = db.Column(
        db.Integer, db.ForeignKey("managed_roles.id"), nullable=False
    )

    second_role_id = db.Column(
        db.Integer, db.ForeignKey("managed_roles.id"), nullable=False
    )

    outcome = db.Column(db.String(30), default="deny", nullable=False)

    enabled = db.Column(db.Boolean, default=True, nullable=False)

    first_role = db.relationship("ManagedRole", foreign_keys=[first_role_id])

    second_role = db.relationship("ManagedRole", foreign_keys=[second_role_id])

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
        db.CheckConstraint(
            "first_role_id < second_role_id",
            name="ck_sod_rules_role_order",
        ),
        db.CheckConstraint(
            "outcome IN ('deny', 'requires_review')",
            name="ck_sod_rules_valid_outcome",
        ),
        db.UniqueConstraint(
            "first_role_id",
            "second_role_id",
            name="uq_sod_rules_role_pair",
        ),
    )
