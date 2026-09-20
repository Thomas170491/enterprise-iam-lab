from extensions import db


class AccessReviewItem(db.Model):
    """
    Represent an identity's role captured for an access review.

    Store identity and role details as a snapshot so the review
    preserves what was observed when the item was created.
    """

    __tablename__ = "access_review_items"

    id = db.Column(db.Integer, primary_key=True)

    review_id = db.Column(
        db.Integer,
        db.ForeignKey("access_reviews.id"),
        nullable=False,
        index=True,
    )

    user_id = db.Column(db.String(255), nullable=False)

    username = db.Column(db.String(255), nullable=False)

    client_name = db.Column(db.String(100), nullable=False)

    role_id = db.Column(db.String(255), nullable=False)

    role_name = db.Column(db.String(100), nullable=False)

    created_at = db.Column(
        db.DateTime(timezone=True),
        server_default=db.func.now(),
        nullable=False,
    )

    review = db.relationship(
        "AccessReview",
        backref="items",
    )

    __table_args__ = (
        db.UniqueConstraint(
            "review_id",
            "user_id",
            "client_name",
            "role_id",
            name="uq_access_review_items_review_user_client_role",
        ),
    )
