from datetime import datetime

from sqlalchemy.dialects.postgresql import JSONB

from app.extensions import db


class Proposal(db.Model):
    __tablename__ = "proposals"

    proposal_id = db.Column(
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

    linked_transcript_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "transcripts.transcript_id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    scope_of_work = db.Column(
        db.Text,
        nullable=False,
    )

    deliverables_list = db.Column(
        JSONB,
        nullable=False,
    )

    timeline_milestones = db.Column(
        JSONB,
        nullable=False,
    )

    version = db.Column(
        db.Integer,
        default=1,
        nullable=False,
    )

    status = db.Column(
        db.String(20),
    )

    generated_by = db.Column(
        db.String(20),
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    # ======================================
    # Relationships
    # ======================================

    client = db.relationship(
        "Client",
        back_populates="proposals",
    )

    created_by = db.relationship(
        "User",
        back_populates="created_proposals",
        foreign_keys=[created_by_user_id],
    )

    transcript = db.relationship(
        "Transcript",
        back_populates="proposals",
    )

    quotes = db.relationship(
        "Quote",
        back_populates="proposal",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # ======================================
    # Serialization
    # ======================================

    def to_dict(self):
        return {
            "proposal_id": self.proposal_id,
            "client_id": self.client_id,
            "created_by_user_id": self.created_by_user_id,
            "linked_transcript_id": self.linked_transcript_id,
            "scope_of_work": self.scope_of_work,
            "deliverables_list": self.deliverables_list,
            "timeline_milestones": self.timeline_milestones,
            "version": self.version,
            "status": self.status,
            "generated_by": self.generated_by,
            "created_at": (
                self.created_at.isoformat()
                if self.created_at
                else None
            ),
        }

    def __repr__(self):
        return (
            f"<Proposal {self.proposal_id} "
            f"Version={self.version}>"
        )