from flask import Blueprint, jsonify, request

from app.services.call_record_service import CallRecordService

call_records_bp = Blueprint(
    "call_records",
    __name__,
)


@call_records_bp.get("/call-records")
def list_call_records():

    result = CallRecordService.list_call_records(
        request.args
    )

    return jsonify(result), 200


@call_records_bp.get("/call-records/<int:call_id>")
def get_call_record(call_id):

    result = CallRecordService.get_call_record(
        call_id
    )

    if result is None:
        return (
            jsonify(
                {"error": "Call record not found"}
            ),
            404,
        )

    return jsonify(result), 200