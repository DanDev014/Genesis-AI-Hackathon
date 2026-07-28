from flask import Blueprint, jsonify, request

from app.services.summary_service import SummaryService

summaries_bp = Blueprint(
    "summaries",
    __name__,
)


@summaries_bp.get("/summaries")
def list_summaries():
    """
    GET /api/summaries
    """

    result = SummaryService.list_summaries(
        request.args
    )

    return jsonify(result), 200


@summaries_bp.get("/summaries/<int:summary_id>")
def get_summary(summary_id):
    """
    GET /api/summaries/<id>
    """

    result = SummaryService.get_summary(
        summary_id
    )

    return jsonify(result), 200


@summaries_bp.post("/summaries")
def create_summary():
    """
    POST /api/summaries
    """

    result = SummaryService.create_summary(
        request.get_json(silent=True)
    )

    return jsonify(result), 201

@summaries_bp.patch("/summaries/<int:summary_id>")
def update_summary(summary_id):
    """
    PATCH /api/summaries/<id>
    """

    result = SummaryService.update_summary(
        summary_id,
        request.get_json(silent=True),
    )

    return jsonify(result), 200


@summaries_bp.post("/summaries/<int:summary_id>/send")
def send_summary(summary_id):
    """
    POST /api/summaries/<id>/send

    Body: { to_emails: string[], subject?, message? }
    """

    result = SummaryService.send_summary(
        summary_id,
        request.get_json(silent=True),
    )

    return jsonify(result), 200