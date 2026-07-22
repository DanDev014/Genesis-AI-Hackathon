from app.extensions import db


class Summary(db.Model):
    __tablename__ = "summaries"

    summary_id = db.Column(
        db.Integer,
        primary_key=True,
    )

    user_id = db.Column(
    db.Integer,
    db.ForeignKey("users.user_id"),
    nullable=False,
)

    client_id = db.Column(
        db.Integer,
        db.ForeignKey("clients.client_id"),
        nullable=False,
    )

    first_meeting_deliverables = db.Column(
        db.JSON,
        nullable=True,
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
    )

    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True,
    )

    # ======================================
    # Relationships
    # ======================================

    # user = db.relationship(
    #     "User",
    #     back_populates="summaries",
    # )

    # client = db.relationship(
    #     "Client",
    #     back_populates="summaries",
    # )

    # ======================================
    # Serialization
    # ======================================

    def to_dict(self):
        return {
            "summary_id": self.summary_id,
            "user_id": self.user_id,
            "client_id": self.client_id,
            "first_meeting_deliverables": self.first_meeting_deliverables,
            "created_at": (
                self.created_at.isoformat()
                if self.created_at
                else None
            ),
            "updated_at": (
                self.updated_at.isoformat()
                if self.updated_at
                else None
            ),
        }

    def __repr__(self):
        return (
            f"<Summary {self.summary_id} "
            f"Client={self.client_id}>"
        )