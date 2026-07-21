from sqlalchemy import desc

from app.models.summary import Summary


class SummaryService:

    @staticmethod
    def list_summaries(params):

        page = int(params.get("page", 1))
        limit = int(params.get("limit", 20))

        query = Summary.query

        language = params.get("language")
        if language:
            query = query.filter(
                Summary.language.ilike(language)
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

        summary = Summary.query.filter_by(
            transcript_id=summary_id
        ).first()

        if summary is None:
            return None

        return {
            "summary_id": summary.transcript_id,
            "call_id": summary.call_id,
            "summary": summary.summary,
            "confidence_score": (
                float(summary.confidence_score)
                if summary.confidence_score is not None
                else None
            ),
            "language": summary.language,
            "created_at": (
                summary.created_at.isoformat()
                if summary.created_at
                else None
            ),
        }