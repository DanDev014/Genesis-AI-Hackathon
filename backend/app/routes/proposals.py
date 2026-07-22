from flask import Blueprint, jsonify, request

from app.exceptions import ResourceNotFound
from app.services.proposal_service import ProposalService

proposals_bp = Blueprint(
    "proposals",
    __name__,
)


@proposals_bp.get("/proposals")
def list_proposals():
    """
    GET /api/proposals

    Query Params
    ------------
    client_id
    status
    generated_by
    page
    limit
    sort
    """

    result = ProposalService.list_proposals(request.args)

    return jsonify(result), 200


@proposals_bp.get("/proposals/<int:proposal_id>")
def get_proposal(proposal_id):
    """
    GET /api/proposals/<id>
    """

    proposal = ProposalService.get_proposal(proposal_id)

    if not proposal:
        raise ResourceNotFound("Proposal not found")

    return jsonify(proposal), 200


@proposals_bp.post("/proposals")
def create_proposal():
    proposal = ProposalService.create_proposal(request.json)

    return jsonify({
        "success": True,
        "message": "Proposal created successfully",
        "data": proposal,
    }), 201


@proposals_bp.patch("/proposals/<int:proposal_id>")
def update_proposal(proposal_id):
    """
    PATCH /api/proposals/<id>
    """

    proposal = ProposalService.update_proposal(
        proposal_id, request.get_json(silent=True)
    )

    return jsonify({
        "success": True,
        "message": "Proposal updated successfully",
        "data": proposal,
    }), 200