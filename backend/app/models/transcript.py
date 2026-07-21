from datetime import datetime

from sqlalchemy.dialects.postgresql import JSONB

from app.extensions import db


class Transcript(db.Model):
    __tablename__ = "transcripts"

    transcript_id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True,
    )

    call_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "call_records.call_id",
            ondelete="CASCADE",
        ),
        unique=True,
        nullable=False,
    )

    processed_by_user_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "users.user_id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    raw_text = db.Column(
        db.Text,
        nullable=False,
    )

    speaker_segments = db.Column(
        JSONB,
        nullable=False,
    )

    language = db.Column(
        db.String(10),
        default="en-KE",
        nullable=False,
    )

    confidence_score = db.Column(
        db.Numeric(3, 2),
    )

    summary = db.Column(
        db.Text,
    )

    extracted_fields = db.Column(
        JSONB,
        nullable=False,
    )

    # ======================================
    # Relationships
    # ======================================

    call = db.relationship(
        "CallRecord",
        back_populates="transcript",
    )

    processed_by = db.relationship(
        "User",
        back_populates="processed_transcripts",
        foreign_keys=[processed_by_user_id],
    )

    proposals = db.relationship(
        "Proposal",
        back_populates="transcript",
        passive_deletes=True,
    )

    # ======================================
    # Serialization
    # ======================================

    def to_dict(self):
        return {
            "transcript_id": self.transcript_id,
            "call_id": self.call_id,
            "processed_by_user_id": self.processed_by_user_id,
            "raw_text": self.raw_text,
            "speaker_segments": self.speaker_segments,
            "language": self.language,
            "confidence_score": (
                float(self.confidence_score)
                if self.confidence_score is not None
                else None
            ),
            "summary": self.summary,
            "extracted_fields": self.extracted_fields,
            
        }

    def __repr__(self):
        return (
            f"<Transcript {self.transcript_id} "
            f"Call={self.call_id}>"
        )