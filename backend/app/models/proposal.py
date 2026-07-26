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

    # Best-effort real meeting timestamp (distinct from created_at, which
    # is "when this proposal row was inserted") — powers the
    # time-to-proposal metric. Null for proposals with no real signal for
    # this yet (created outside the transcript-extraction flow, or before
    # this column existed).
    meeting_occurred_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True,
    )

    deliverables_list = db.Column(
        JSONB,
        nullable=False,
    )

    # Client-stated constraints/asks, distinct from deliverables — each item
    # is {"text": str, "checked": bool} so the team can check them off as
    # the engagement satisfies them.
    requirements_checklist = db.Column(
        JSONB,
        nullable=True,
    )

    timeline_milestones = db.Column(
        db.Text,
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

    # Opaque, unguessable token used by the public /p/<token> share link —
    # generated lazily the first time a proposal is sent, never the raw
    # proposal_id (which is sequential and enumerable).
    share_token = db.Column(
        db.String(64),
        unique=True,
        nullable=True,
    )

    sent_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True,
    )

    # Business result of the deal ("pending" | "won" | "lost") — separate
    # from `status` above, which only tracks the document's own lifecycle.
    outcome = db.Column(
        db.String(20),
        default="pending",
        nullable=False,
    )

    # Free-text client feedback captured alongside the outcome.
    outcome_notes = db.Column(
        db.Text,
        nullable=True,
    )

    outcome_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True,
    )

    # Producer sign-off gate. Nothing in this app checked this before the
    # QuickBooks integration — it's the first real "someone reviewed this
    # before it goes further" gate in the backend. One-way: no unapprove.
    approved_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True,
    )

    approved_by_user_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "users.user_id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    # ==================================================
    # Relationships
    # ==================================================

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

    # ==================================================
    # Serialization
    # ==================================================

    def to_dict(self):
        return {
            "proposal_id": self.proposal_id,

            "client": (
                {
                    "client_id": self.client.client_id,
                    "name": self.client.name,
                    "company": self.client.company,
                    "email": self.client.email,
                }
                if self.client
                else None
            ),

            "created_by_user_id": self.created_by_user_id,
            "linked_transcript_id": self.linked_transcript_id,

            # Cleaner API names
            "scope_of_work": self.scope_of_work,
            "deliverables": self.deliverables_list,
            "requirements_checklist": self.requirements_checklist or [],
            "timeline": self.timeline_milestones,

            "version": self.version,
            "status": self.status,
            "generated_by": self.generated_by,

            "sent_at": (
                self.sent_at.isoformat()
                if self.sent_at
                else None
            ),
            "share_token": self.share_token,

            "outcome": self.outcome,
            "outcome_notes": self.outcome_notes,
            "outcome_at": (
                self.outcome_at.isoformat()
                if self.outcome_at
                else None
            ),

            "approved": self.approved_at is not None,
            "approved_at": (
                self.approved_at.isoformat()
                if self.approved_at
                else None
            ),
            "approved_by_user_id": self.approved_by_user_id,

            "created_at": (
                self.created_at.isoformat()
                if self.created_at
                else None
            ),

            "meeting_occurred_at": (
                self.meeting_occurred_at.isoformat()
                if self.meeting_occurred_at
                else None
            ),
            "time_to_proposal_hours": self._time_to_proposal_hours(),
        }

    def _time_to_proposal_hours(self):
        """created_at - meeting_occurred_at, in hours. Both columns are
        `timezone=True` but written with naive datetime.utcnow() — SQLAlchemy
        may hand back either naive (same-request, unflushed) or tz-aware
        (post-commit refresh from Postgres) values, so this strips tzinfo
        from both sides before subtracting rather than assuming one."""
        if not self.created_at or not self.meeting_occurred_at:
            return None
        created = self.created_at.replace(tzinfo=None)
        occurred = self.meeting_occurred_at.replace(tzinfo=None)
        return round((created - occurred).total_seconds() / 3600, 1)

    def to_public_dict(self):
        """Safe subset served by the unauthenticated /p/<token> page — no
        internal user/transcript ids, no client contact details beyond the
        company name, no share_token (the URL itself already is the key)."""
        return {
            "proposal_id": self.proposal_id,

            "client": (
                {"company": self.client.company}
                if self.client
                else None
            ),

            "scope_of_work": self.scope_of_work,
            "deliverables": self.deliverables_list,
            "requirements_checklist": self.requirements_checklist or [],
            "timeline": self.timeline_milestones,

            "version": self.version,
            "status": self.status,

            "created_at": (
                self.created_at.isoformat()
                if self.created_at
                else None
            ),

            "quotes": [quote.to_public_dict() for quote in self.quotes],
        }

    def __repr__(self):
        return (
            f"<Proposal {self.proposal_id} "
            f"Version={self.version}>"
        )