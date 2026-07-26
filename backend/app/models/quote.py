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

    # Full result of the last send-to-QuickBooks attempt — mode, ok/error,
    # the built payload, and whatever QuickBooks (or the simulation) sent
    # back. Null until the quote's been sent at least once.
    quickbooks_result = db.Column(
        JSONB,
        nullable=True,
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
                    "approved": self.proposal.approved_at is not None,
                    "client": (
                        {
                            "name": self.proposal.client.name,
                            "company": self.proposal.client.company,
                        }
                        if self.proposal.client
                        else None
                    ),
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

            # Aliases for the Kora-agent quote shape (renderer.py's
            # _defaults_for_quote) so the frontend doesn't need two
            # different field names depending on which backend served the
            # quote. Not a new column — subtotal is summed from line_items
            # (each already carries a computed "amount") once here instead
            # of every page that displays a quote re-deriving it.
            "total": (
                float(self.total_amount)
                if self.total_amount is not None
                else None
            ),
            "subtotal": sum(
                (item.get("amount") or 0) for item in (self.line_items or [])
            ),

            "validity_days": self.validity_days,

            "status": self.status,

            "line_items": self.line_items,

            "quickbooks_result": self.quickbooks_result,

            "created_at": (
                self.created_at.isoformat()
                if self.created_at
                else None
            ),
        }

    def to_public_dict(self):
        """Safe subset served by the unauthenticated /p/<token> page — no
        internal user id, no nested proposal/client (the page already has
        the proposal it belongs to)."""
        return {
            "quote_id": self.quote_id,
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
            "total": (
                float(self.total_amount)
                if self.total_amount is not None
                else None
            ),
            "subtotal": sum(
                (item.get("amount") or 0) for item in (self.line_items or [])
            ),
            "validity_days": self.validity_days,
            "status": self.status,
            "line_items": self.line_items,
        }

    def __repr__(self):
        return (
            f"<Quote {self.quote_id} | "
            f"Proposal={self.proposal_id} | "
            f"{self.currency} {self.total_amount}>"
        )