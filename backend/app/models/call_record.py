from datetime import datetime

from sqlalchemy.dialects.postgresql import JSONB

from app.extensions import db


class CallRecord(db.Model):
    __tablename__ = "call_records"

    call_id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True,
    )

    client_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "clients.client_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    created_by_user_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "users.user_id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    meeting_time = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
    )

    duration_minutes = db.Column(
        db.Integer,
        nullable=False,
    )

    call_type = db.Column(
        db.String(30),
    )

    recording_url = db.Column(
        db.Text,
    )

    platform = db.Column(
        db.String(30),
        default="Google Meet",
        nullable=False,
    )

    participants = db.Column(
        JSONB,
        nullable=False,
    )

    # ======================================
    # Relationships
    # ======================================

    client = db.relationship(
        "Client",
        back_populates="calls",
    )

    created_by = db.relationship(
        "User",
        back_populates="created_calls",
        foreign_keys=[created_by_user_id],
    )

    transcript = db.relationship(
        "Transcript",
        back_populates="call",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # ======================================
    # Serialization
    # ======================================

    def to_dict(self):
        return {
            "call_id": self.call_id,
            "client_id": self.client_id,
            "created_by_user_id": self.created_by_user_id,
            "meeting_time": (
                self.meeting_time.isoformat()
                if self.meeting_time
                else None
            ),
            "duration_minutes": self.duration_minutes,
            "call_type": self.call_type,
            "recording_url": self.recording_url,
            "platform": self.platform,
            "participants": self.participants,
        }

    def __repr__(self):
        return (
            f"<CallRecord {self.call_id} "
            f"Client={self.client_id}>"
        )