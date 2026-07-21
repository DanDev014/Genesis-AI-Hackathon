from datetime import UTC, datetime

from sqlalchemy import desc

from app.extensions import db
from app.exceptions import (
    DatabaseError,
    ResourceNotFound,
    ValidationError,
)
from app.models.summary import Summary


class SummaryService:

    @staticmethod
    def list_summaries(params):
        """
        GET /api/summaries
        """

        page = int(params.get("page", 1))
        limit = int(params.get("limit", 20))

        query = Summary.query

        client_id = params.get("client_id")
        if client_id:
            query = query.filter(
                Summary.client_id == client_id
            )

        sort = params.get(
            "sort",
            "created_at_desc",
        )

        if sort == "created_at_asc":
            query = query.order_by(
                Summary.created_at.asc()
            )
        else:
            query = query.order_by(
                desc(Summary.created_at)
            )

        pagination = query.paginate(
            page=page,
            per_page=limit,
            error_out=False,
        )

        return {
            "success": True,
            "data": [
                summary.to_dict()
                for summary in pagination.items
            ],
            "meta": {
                "page": pagination.page,
                "limit": pagination.per_page,
                "total": pagination.total,
                "pages": pagination.pages,
            },
        }

    @staticmethod
    def get_summary(summary_id):
        """
        GET /api/summaries/<id>
        """

        summary = Summary.query.filter_by(
            summary_id=summary_id
        ).first()

        if summary is None:
            raise ResourceNotFound(
                "Summary not found"
            )

        return {
            "success": True,
            "data": summary.to_dict(),
        }

    @staticmethod
    def create_summary(data):
        """
        POST /api/summaries
        """

        if not data:
            raise ValidationError(
                "Request body is required"
            )

        if not data.get("client_id"):
            raise ValidationError(
                "client_id is required"
            )

        if not data.get(
            "first_meeting_deliverables"
        ):
            raise ValidationError(
                "first_meeting_deliverables is required"
            )

        try:

            summary = Summary(
                client_id=data["client_id"],
                first_meeting_deliverables=data[
                    "first_meeting_deliverables"
                ],
                created_at=datetime.now(UTC),
            )

            db.session.add(summary)
            db.session.commit()

            return {
                "success": True,
                "message": (
                    "Summary created successfully"
                ),
                "data": summary.to_dict(),
            }

        except Exception:
            db.session.rollback()

            raise DatabaseError(
                "Unable to create summary."
            )

    @staticmethod
    def update_summary(summary_id, data):
        """
        PATCH /api/summaries/<id>
        """

        if not data:
            raise ValidationError(
                "Request body is required"
            )

        summary = Summary.query.filter_by(
            summary_id=summary_id
        ).first()

        if summary is None:
            raise ResourceNotFound(
                "Summary not found"
            )

        meeting = data.get(
            "first_meeting_deliverables"
        )

        if meeting is None:
            raise ValidationError(
                "first_meeting_deliverables is required"
            )

        try:
            summary.first_meeting_deliverables = meeting

            db.session.commit()

            return {
                "success": True,
                "message": (
                    "Summary updated successfully"
                ),
                "data": summary.to_dict(),
            }

        except Exception:
            db.session.rollback()

            raise DatabaseError(
                "Unable to update summary."
            )