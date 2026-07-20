from flask import Blueprint, jsonify
from sqlalchemy import text

from app.extensions import db

test_bp = Blueprint("test", __name__)


@test_bp.get("/health")
def health():
    try:
        result = db.session.execute(text("SELECT 1")).scalar()

        return jsonify(
            {
                "success": True,
                "database": "connected",
                "result": result,
            }
        ), 200

    except Exception as e:
        return jsonify(
            {
                "success": False,
                "database": "disconnected",
                "error": str(e),
            }
        ), 500