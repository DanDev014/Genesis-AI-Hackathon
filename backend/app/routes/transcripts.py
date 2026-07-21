from flask import Blueprint, jsonify

transcripts_bp = Blueprint("transcripts", __name__)


@transcripts_bp.route("/transcripts", methods=["GET"])
def get_transcripts():
    return jsonify({
        "success": True,
        "message": "Transcript routes are available.",
        "data": []
    }), 200