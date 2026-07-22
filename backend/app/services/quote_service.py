from sqlalchemy import desc

from app.extensions import db
from app.models.quote import Quote
from app.exceptions import (
    DatabaseError,
    ResourceNotFound,
    ValidationError,
)


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

    @staticmethod
    def create_quote(data):

        quote = Quote(
            proposal_id=data["proposal_id"],
            created_by_user_id=data["user_id"],

            currency=data.get("currency", "KES"),

            total_amount=data["total_amount"],

            line_items=data["line_items"],

            status="draft",
        )

        db.session.add(quote)
        db.session.commit()

        return quote.to_dict()

    @staticmethod
    def update_quote(quote_id, data):
        """
        PATCH /api/quotes/<id>

        line_items also recomputes total_amount so a manager's pricing
        edit stays consistent with what actually gets quoted.
        """

        if not data:
            raise ValidationError(
                "Request body is required"
            )

        quote = Quote.query.get(quote_id)

        if quote is None:
            raise ResourceNotFound("Quote not found")

        if "line_items" in data:
            items = []
            for item in data["line_items"]:
                item = dict(item)
                item.setdefault("qty", 1)
                item.setdefault("unit_price", 0)
                item["amount"] = item.get("amount") or round(
                    item["qty"] * item["unit_price"], 2
                )
                items.append(item)

            quote.line_items = items
            quote.total_amount = round(
                sum(item["amount"] for item in items), 2
            )

        if "currency" in data:
            quote.currency = data["currency"][:5]

        if "tax_rate" in data:
            quote.tax_rate = data["tax_rate"]

        if "discount_amount" in data:
            quote.discount_amount = data["discount_amount"]

        if "validity_days" in data:
            quote.validity_days = data["validity_days"]

        if "status" in data:
            quote.status = data["status"]

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()

            raise DatabaseError(
                "Unable to update quote."
            )

        return quote.to_dict()