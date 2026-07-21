from sqlalchemy.orm import joinedload

from app.models.call_record import CallRecord


class CallRecordService:

    @staticmethod
    def list_call_records(args):
        page = max(int(args.get("page", 1)), 1)
        limit = min(max(int(args.get("limit", 20)), 1), 100)

        client_id = args.get("client_id")
        call_type = args.get("call_type")
        platform = args.get("platform")
        sort = args.get("sort", "-meeting_time")

        query = (
            CallRecord.query.options(
                joinedload(CallRecord.client),
                joinedload(CallRecord.transcript),
            )
        )

        # -----------------------------
        # Filters
        # -----------------------------
        if client_id:
            query = query.filter(
                CallRecord.client_id == client_id
            )

        if call_type:
            query = query.filter(
                CallRecord.call_type == call_type
            )

        if platform:
            query = query.filter(
                CallRecord.platform == platform
            )

        # -----------------------------
        # Sorting
        # -----------------------------
        if sort.startswith("-"):
            field = sort[1:]
            column = getattr(
                CallRecord,
                field,
                CallRecord.meeting_time,
            )
            query = query.order_by(column.desc())
        else:
            column = getattr(
                CallRecord,
                sort,
                CallRecord.meeting_time,
            )
            query = query.order_by(column.asc())

        pagination = query.paginate(
            page=page,
            per_page=limit,
            error_out=False,
        )

        data = []

        for call in pagination.items:

            data.append(
                {
                    "call_id": call.call_id,
                    "client_id": call.client_id,
                    "client_name": (
                        call.client.name
                        if call.client
                        else None
                    ),
                    "meeting_time": (
                        call.meeting_time.isoformat()
                        if call.meeting_time
                        else None
                    ),
                    "duration_minutes": call.duration_minutes,
                    "call_type": call.call_type,
                    "platform": call.platform,
                    "has_transcript": (
                        call.transcript is not None
                    ),
                }
            )

        return {
            "data": data,
            "meta": {
                "page": page,
                "limit": limit,
                "total": pagination.total,
            },
        }

    @staticmethod
    def get_call_record(call_id):

        call = (
            CallRecord.query.options(
                joinedload(CallRecord.client),
                joinedload(CallRecord.transcript),
            )
            .filter_by(call_id=call_id)
            .first()
        )

        if call is None:
            return None

        transcript = None

        if call.transcript:
            transcript = {
                "transcript_id": call.transcript.transcript_id,
                "summary": call.transcript.summary,
                "confidence_score": (
                    float(call.transcript.confidence_score)
                    if call.transcript.confidence_score is not None
                    else None
                ),
            }

        return {
            "call_id": call.call_id,
            "client": {
                "client_id": call.client.client_id,
                "name": call.client.name,
            }
            if call.client
            else None,
            "meeting_time": (
                call.meeting_time.isoformat()
                if call.meeting_time
                else None
            ),
            "duration_minutes": call.duration_minutes,
            "call_type": call.call_type,
            "platform": call.platform,
            "participants": call.participants,
            "recording_url": call.recording_url,
            "transcript": transcript,
        }