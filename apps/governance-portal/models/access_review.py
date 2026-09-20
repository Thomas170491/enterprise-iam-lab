from extensions import db


class AccessReview(db.Model):
    """
    Represent an access review campaign and its assigned reviewer.
    """

    __tablename__ = "access_reviews"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(200), nullable=False)

    created_by_user_id = db.Column(db.String(255), nullable=False)

    reviewer_user_id = db.Column(db.String(255), nullable=False)

    status = db.Column(db.String(20), default="draft", nullable=False)

    created_at = db.Column(
        db.DateTime(timezone=True), server_default=db.func.now(), nullable=False
    )

    updated_at = db.Column(
        db.DateTime(timezone=True),
        server_default=db.func.now(),
        onupdate=db.func.now(),
        nullable=False,
    )

    due_at = db.Column(db.DateTime(timezone=True), nullable=True)

    __table_args__ = (
        db.CheckConstraint(
            "status IN ('draft', 'open', 'completed', 'cancelled')",
            name="ck_access_reviews_valid_status",
        ),
    )
