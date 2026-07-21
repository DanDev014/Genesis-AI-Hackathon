from flask import Blueprint, jsonify, request

from app.services.summary_service import SummaryService

summaries_bp = Blueprint(
    "summaries",
    __name__,
)


@summaries_bp.get("/summaries")
def list_summaries():

    result = SummaryService.list_summaries(
        request.args
    )

    return jsonify(result), 200


@summaries_bp.get("/summaries/<int:summary_id>")
def get_summary(summary_id):

    result = SummaryService.get_summary(
        summary_id
    )

    if result is None:
        return jsonify(
            {
                "error": "Summary not found"
            }
        ), 404

    return jsonify(result), 200