from flask import Blueprint, jsonify

from app.services.report_service import ReportService

reports_bp = Blueprint(
    "reports",
    __name__,
)


@reports_bp.get("/dashboard")
def get_dashboard():
    """
    GET /api/dashboard
    """

    result = ReportService.get_dashboard()

    return jsonify(result), 200
