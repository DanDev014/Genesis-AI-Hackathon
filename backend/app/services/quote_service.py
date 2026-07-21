from sqlalchemy import desc

from app.models.quote import Quote


class QuoteService:

    @staticmethod
    def list_quotes(params):

        page = int(params.get("page", 1))
        limit = int(params.get("limit", 20))

        query = Quote.query

        # -------------------------------
        # Filters
        # -------------------------------

        status = params.get("status")
        if status:
            query = query.filter(
                Quote.status.ilike(status)
            )

        proposal_id = params.get("proposal_id")
        if proposal_id:
            query = query.filter(
                Quote.proposal_id == proposal_id
            )

        currency = params.get("currency")
        if currency:
            query = query.filter(
                Quote.currency.ilike(currency)
            )

        # -------------------------------
        # Sorting
        # -------------------------------

        sort = params.get(
            "sort",
            "created_at_desc",
        )

        if sort == "amount_asc":
            query = query.order_by(
                Quote.total_amount.asc()
            )

        elif sort == "amount_desc":
            query = query.order_by(
                Quote.total_amount.desc()
            )

        elif sort == "created_at_asc":
            query = query.order_by(
                Quote.created_at.asc()
            )

        else:
            query = query.order_by(
                desc(
                    Quote.created_at
                )
            )

        pagination = query.paginate(
            page=page,
            per_page=limit,
            error_out=False,
        )

        return {
            "data": [
                quote.to_dict()
                for quote in pagination.items
            ],
            "meta": {
                "page": pagination.page,
                "limit": pagination.per_page,
                "total": pagination.total,
                "pages": pagination.pages,
            },
        }

    @staticmethod
    def get_quote(quote_id):

        quote = Quote.query.filter_by(
            quote_id=quote_id
        ).first()

        if not quote:
            return None

        return quote.to_dict()