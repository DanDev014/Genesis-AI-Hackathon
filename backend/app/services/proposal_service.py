from sqlalchemy import asc, desc

from app.models.proposal import Proposal
from app.extensions import db
from app.exceptions import (
    DatabaseError,
    ResourceNotFound,
    ValidationError,
)

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