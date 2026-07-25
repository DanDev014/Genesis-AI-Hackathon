import secrets
from datetime import datetime

from sqlalchemy import asc, desc

from app.models.proposal import Proposal
from app.extensions import db
from app.exceptions import (
    DatabaseError,
    ResourceNotFound,
    ValidationError,
)
from app.services.email_service import send_email

class ProposalService:

    @staticmethod
    def list_proposals(params):

        query = Proposal.query

        # ------------------------
        # Filters
        # ------------------------
        client_id = params.get("client_id")
        if client_id:
            query = query.filter(
                Proposal.client_id == client_id
            )

        status = params.get("status")
        if status:
            query = query.filter(
                Proposal.status == status
            )

        generated_by = params.get("generated_by")
        if generated_by:
            query = query.filter(
                Proposal.generated_by == generated_by
            )

        # ------------------------
        # Sorting
        # ------------------------
        sort = params.get("sort", "-created_at")

        if sort.startswith("-"):
            column = getattr(
                Proposal,
                sort[1:],
                Proposal.created_at,
            )
            query = query.order_by(desc(column))
        else:
            column = getattr(
                Proposal,
                sort,
                Proposal.created_at,
            )
            query = query.order_by(asc(column))

        # ------------------------
        # Pagination
        # ------------------------
        page = int(params.get("page", 1))
        limit = int(params.get("limit", 20))

        pagination = query.paginate(
            page=page,
            per_page=limit,
            error_out=False,
        )

        return {
            "data": [
                proposal.to_dict()
                for proposal in pagination.items
            ],
            "meta": {
                "page": page,
                "limit": limit,
                "total": pagination.total,
                "pages": pagination.pages,
            },
        }

    @staticmethod
    def get_proposal(proposal_id):

        proposal = Proposal.query.get(proposal_id)

        if not proposal:
            return None

        return proposal.to_dict()


    @staticmethod
    def create_proposal(data):

        proposal = Proposal(
            client_id=data["client_id"],

            created_by_user_id=data["user_id"],

            linked_transcript_id=data.get("transcript_id"),

            scope_of_work=data["scope_of_work"],

            deliverables_list=data["deliverables_list"],

            timeline_milestones=data["timeline_milestones"],

            generated_by=data.get("generated_by", "ai"),

            status=data.get("status", "draft"),
        )

        db.session.add(proposal)
        db.session.commit()

        return proposal.to_dict()

    @staticmethod
    def update_proposal(proposal_id, data):
        """
        PATCH /api/proposals/<id>

        Lets a manager revise a draft before approving it. Only touches
        fields actually present in the body — a PATCH, not a full replace.
        """

        if not data:
            raise ValidationError(
                "Request body is required"
            )

        proposal = Proposal.query.get(proposal_id)

        if proposal is None:
            raise ResourceNotFound("Proposal not found")

        if "scope_of_work" in data:
            proposal.scope_of_work = data["scope_of_work"]

        if "deliverables_list" in data:
            proposal.deliverables_list = data["deliverables_list"]

        if "timeline_milestones" in data:
            proposal.timeline_milestones = data["timeline_milestones"]

        if "status" in data:
            proposal.status = data["status"]

        if "version" in data:
            proposal.version = data["version"]

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()

            raise DatabaseError(
                "Unable to update proposal."
            )

        return proposal.to_dict()

    @staticmethod
    def get_public_proposal(token):
        """Look up a proposal by its unguessable share token — this, not a
        JWT, is the access boundary for the client-facing /p/<token> page."""

        if not token:
            return None

        proposal = Proposal.query.filter_by(share_token=token).first()

        if not proposal:
            return None

        return proposal.to_public_dict()

    @staticmethod
    def send_proposal(proposal_id, data):
        """
        POST /api/proposals/<id>/send

        Generates the share link (once, reused on every subsequent send),
        emails it to the given address, and marks the proposal as sent.
        """
        from flask import current_app

        if not data or not (data.get("to_email") or "").strip():
            raise ValidationError("Recipient email is required")

        proposal = Proposal.query.get(proposal_id)

        if proposal is None:
            raise ResourceNotFound("Proposal not found")

        if not proposal.share_token:
            proposal.share_token = secrets.token_urlsafe(24)

        share_url = f"{current_app.config.get('PUBLIC_APP_URL')}/p/{proposal.share_token}"

        company = proposal.client.company if proposal.client else "your project"
        subject = (data.get("subject") or "").strip() or f"Your proposal from Kora AI — {company}"
        message = (data.get("message") or "").strip() or (
            "Please find your proposal ready for review. Click below to view "
            "the full scope, timeline, and pricing."
        )

        # Send before committing anything — if delivery fails we don't want
        # a half-applied "sent" state sitting in the database.
        send_email(
            to_email=data["to_email"].strip(),
            subject=subject,
            heading="Your proposal is ready",
            message=message,
            cta_label="View proposal",
            cta_url=share_url,
        )

        proposal.status = "sent"
        proposal.sent_at = datetime.utcnow()

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise DatabaseError("Email sent, but failed to update the proposal record.")

        result = proposal.to_dict()
        result["share_url"] = share_url
        return result