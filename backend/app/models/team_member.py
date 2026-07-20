from datetime import datetime

from app.extensions import db


class TeamMember(db.Model):
    __tablename__ = "team_members"

    staff_id = db.Column(
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

    full_name = db.Column(
        db.String(100),
        nullable=False,
    )

    role_category = db.Column(
        db.String(20),
        nullable=False,
    )

    role = db.Column(
        db.String(50),
        nullable=False,
    )

    skills = db.Column(
        db.ARRAY(db.Text),
        default=list,
        nullable=False,
    )

    rate_per_hour = db.Column(
        db.Numeric(10, 2),
        nullable=False,
    )

    performance_rating = db.Column(
        db.Numeric(2, 1),
    )

    is_available = db.Column(
        db.Boolean,
        default=True,
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

    user = db.relationship(
        "User",
        back_populates="team_member",
    )

    managed_clients = db.relationship(
        "Client",
        back_populates="account_manager",
        passive_deletes=True,
    )

    # ======================================
    # Serialization
    # ======================================

    def to_dict(self):
        return {
            "staff_id": self.staff_id,
            "user_id": self.user_id,
            "full_name": self.full_name,
            "role_category": self.role_category,
            "role": self.role,
            "skills": self.skills,
            "rate_per_hour": (
                float(self.rate_per_hour)
                if self.rate_per_hour is not None
                else None
            ),
            "performance_rating": (
                float(self.performance_rating)
                if self.performance_rating is not None
                else None
            ),
            "is_available": self.is_available,
            "created_at": (
                self.created_at.isoformat()
                if self.created_at
                else None
            ),
        }

    def __repr__(self):
        return (
            f"<TeamMember {self.staff_id} - "
            f"{self.full_name}>"
        )