from datetime import UTC, datetime

from sqlalchemy import desc

from app.extensions import db
from app.exceptions import (
    DatabaseError,
    ResourceNotFound,
    ValidationError,
)
from app.models.summary import Summary
from app.services.email_service import send_email


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
                user_id=data["user_id"],
                client_id=data["client_id"],
                first_meeting_deliverables=data["first_meeting_deliverables"],
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

    @staticmethod
    def send_summary(summary_id, data):
        """
        POST /api/summaries/<id>/send

        Body: { to_emails: string[], subject?: str, message?: str }

        Internal, team-facing — unlike proposal sending, this doesn't
        generate a public share token. Recipients are expected to already
        have an account, so the CTA just links to the normal (login-gated)
        summary page.
        """
        from flask import current_app

        if not data or not data.get("to_emails"):
            raise ValidationError("At least one recipient email is required")

        to_emails = [e.strip() for e in data["to_emails"] if e and e.strip()]
        if not to_emails:
            raise ValidationError("At least one recipient email is required")

        summary = Summary.query.filter_by(summary_id=summary_id).first()

        if summary is None:
            raise ResourceNotFound("Summary not found")

        meeting = summary.first_meeting_deliverables or {}
        key_points = meeting.get("key_points", meeting) if isinstance(meeting, dict) else {}
        client_info = (key_points or {}).get("client") or {}
        company = client_info.get("company") or (summary.client.company if summary.client else "a client")
        meeting_title = meeting.get("title") if isinstance(meeting, dict) else None

        subject = (data.get("subject") or "").strip() or f"Discovery call summary — {company}"
        message = (data.get("message") or "").strip() or (
            f"The discovery call with {company} has been processed. "
            "Click below to see the full summary, key points, and open questions."
        )

        summary_url = f"{current_app.config.get('PUBLIC_APP_URL')}/summaries/{summary.summary_id}"

        send_email(
            to_email=to_emails,
            subject=subject,
            heading=meeting_title or "Discovery call summary",
            message=message,
            cta_label="View summary",
            cta_url=summary_url,
        )

        return {
            "success": True,
            "message": f"Summary sent to {len(to_emails)} recipient(s).",
            "data": summary.to_dict(),
        }