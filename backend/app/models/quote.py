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
            "proposal_id": self.proposal_id,
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
            "created_at": (
                self.created_at.isoformat()
                if self.created_at
                else None
            ),
        }

    def __repr__(self):
        return (
            f"<Quote {self.quote_id} "
            f"Amount={self.total_amount} {self.currency}>"
        )