from datetime import datetime

from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


class User(db.Model):
    __tablename__ = "users"

    user_id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True,
    )

    email = db.Column(
        db.String(100),
        unique=True,
        nullable=False,
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False,
    )

    user_type = db.Column(
        db.String(20),
        nullable=False,
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    # ==========================
    # Relationships
    # ==========================

    team_member = db.relationship(
        "TeamMember",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    client = db.relationship(
        "Client",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    created_calls = db.relationship(
        "CallRecord",
        back_populates="created_by",
        foreign_keys="CallRecord.created_by_user_id",
    )

    processed_transcripts = db.relationship(
        "Transcript",
        back_populates="processed_by",
        foreign_keys="Transcript.processed_by_user_id",
    )

    created_proposals = db.relationship(
        "Proposal",
        back_populates="created_by",
        foreign_keys="Proposal.created_by_user_id",
    )

    created_quotes = db.relationship(
        "Quote",
        back_populates="created_by",
        foreign_keys="Quote.created_by_user_id",
    )

    # ==========================
    # Password Helpers
    # ==========================

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str):
        return check_password_hash(
            self.password_hash,
            password,
        )

    # ==========================
    # Serialization
    # ==========================

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "email": self.email,
            "user_type": self.user_type,
            "created_at": (
                self.created_at.isoformat()
                if self.created_at
                else None
            ),
        }

    def __repr__(self):
        return (
            f"<User {self.user_id} - {self.email}>"
        )