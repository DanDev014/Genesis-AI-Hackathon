from datetime import datetime

from sqlalchemy.dialects.postgresql import JSONB

from app.extensions import db


class Quote(db.Model):
    __tablename__ = "quotes"

    quote_id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True,
    )

    proposal_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "proposals.proposal_id",
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

    currency = db.Column(
        db.String(5),
        default="KES",
        nullable=False,
    )

    tax_rate = db.Column(
        db.Numeric(4, 2),
        default=16.00,
        nullable=False,
    )

    discount_amount = db.Column(
        db.Numeric(10, 2),
        default=0.00,
        nullable=False,
    )

    total_amount = db.Column(
        db.Numeric(12, 2),
        nullable=False,
    )

    validity_days = db.Column(
        db.Integer,
        default=30,
        nullable=False,
    )

    status = db.Column(
        db.String(20),
        nullable=False,
    )

    line_items = db.Column(
        JSONB,
        nullable=False,
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    # ======================================
    # Relationships
    # ======================================

    proposal = db.relationship(
        "Proposal",
        back_populates="quotes",
    )

    created_by = db.relationship(
        "User",
        back_populates="created_quotes",
        foreign_keys=[created_by_user_id],
    )

    summary = db.relationship(
        "Summary",
        back_populates="quote",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # ======================================
    # Serialization
    # ======================================

    def to_dict(self):
        return {
            "quote_id": self.quote_id,

            "proposal": (
                {
                    "proposal_id": self.proposal.proposal_id,
                    "client_id": self.proposal.client_id,
                    "version": self.proposal.version,
                    "status": self.proposal.status,
                }
                if self.proposal
                else None
            ),

            "created_by_user_id": self.created_by_user_id,

            "currency": self.currency,

            "tax_rate": (
                float(self.tax_rate)
                if self.tax_rate is not None
                else None
            ),

            "discount_amount": (
                float(self.discount_amount)
                if self.discount_amount is not None
                else None
            ),

            "total_amount": (
                float(self.total_amount)
                if self.total_amount is not None
                else None
            ),

            "validity_days": self.validity_days,

            "status": self.status,

            "line_items": self.line_items,

            "summary": (
                {
                    "summary_id": self.summary.summary_id,
                    "client_id": self.summary.client_id,
                    "proposal_id": self.summary.proposal_id,
                    "quote_id": self.summary.quote_id,
                    "first_meeting_deliverables": self.summary.first_meeting_deliverables,
                    "created_at": (
                        self.summary.created_at.isoformat()
                        if self.summary.created_at
                        else None
                    ),
                }
                if self.summary
                else None
            ),

            "created_at": (
                self.created_at.isoformat()
                if self.created_at
                else None
            ),
        }

    def __repr__(self):
        return (
            f"<Quote {self.quote_id} | "
            f"Proposal={self.proposal_id} | "
            f"{self.currency} {self.total_amount}>"
        )