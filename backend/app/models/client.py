from datetime import datetime

from app.extensions import db


class Client(db.Model):
    __tablename__ = "clients"

    client_id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True,
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.user_id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    name = db.Column(
        db.String(100),
        nullable=False,
    )

    company = db.Column(
        db.String(100),
        nullable=False,
    )

    industry = db.Column(
        db.String(50),
        nullable=False,
    )

    phone = db.Column(
        db.String(20),
    )

    email = db.Column(
        db.String(100),
        unique=True,
        nullable=False,
    )

    source = db.Column(
        db.String(30),
    )

    status = db.Column(
        db.String(30),
    )

    summaries = db.relationship(
    "Summary",
    back_populates="client",
)

    assigned_account_manager = db.Column(
        db.Integer,
        db.ForeignKey(
            "team_members.staff_id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    # ==================================================
    # Relationships
    # ==================================================

    user = db.relationship(
        "User",
        back_populates="client",
    )

    account_manager = db.relationship(
        "TeamMember",
        back_populates="managed_clients",
    )

    calls = db.relationship(
        "CallRecord",
        back_populates="client",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    proposals = db.relationship(
        "Proposal",
        back_populates="client",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # ==================================================
    # Serialization
    # ==================================================

    def to_dict(self):
        latest_call = (
            max(
                self.calls,
                key=lambda c: c.meeting_time,
            )
            if self.calls
            else None
        )

        return {
            "client_id": self.client_id,
            "user_id": self.user_id,
            "name": self.name,
            "company": self.company,
            "industry": self.industry,
            "phone": self.phone,
            "email": self.email,
            "source": self.source,
            "status": self.status,
            "assigned_account_manager": (
                {
                    "staff_id": self.account_manager.staff_id,
                    "full_name": self.account_manager.full_name,
                }
                if self.account_manager
                else None
            ),
            "last_call_at": (
                latest_call.meeting_time.isoformat()
                if latest_call
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
            f"<Client {self.client_id} - "
            f"{self.company}>"
        )