from app.extensions import db


class Summary(db.Model):
    __tablename__ = "summaries"

    summary_id = db.Column(
        db.Integer,
        primary_key=True,
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