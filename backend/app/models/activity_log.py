from datetime import datetime

from sqlalchemy.dialects.postgresql import JSONB

from app.extensions import db


class ActivityLog(db.Model):
    """User-attributed event log — "who did what, when" for a proposal or
    quote. Distinct from the dashboard's "recent activity" feed, which is
    just a synthesized view over created_at timestamps on existing rows."""

    __tablename__ = "activity_logs"

    activity_log_id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True,
    )

    entity_type = db.Column(
        db.String(20),
        nullable=False,
    )

    entity_id = db.Column(
        db.Integer,
        nullable=False,
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
    )

    action = db.Column(
        db.String(40),
        nullable=False,
    )

    details = db.Column(
        JSONB,
        nullable=True,
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    user = db.relationship("User")

    def to_dict(self):
        return {
            "activity_log_id": self.activity_log_id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "user_id": self.user_id,
            "user_email": self.user.email if self.user else None,
            "action": self.action,
            "details": self.details,
            "created_at": (
                self.created_at.isoformat()
                if self.created_at
                else None
            ),
        }

    def __repr__(self):
        return f"<ActivityLog {self.entity_type}#{self.entity_id} {self.action}>"
