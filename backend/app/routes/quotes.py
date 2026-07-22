from flask import Blueprint, jsonify, request

from app.services.quote_service import QuoteService

quotes_bp = Blueprint(
    "quotes",
    __name__,
)


@quotes_bp.get("/quotes")
def list_quotes():
    """
    GET /api/quotes

    Query Params
    ------------
    page
    limit
    status
    proposal_id
    currency
    sort
    """

    result = QuoteService.list_quotes(
        request.args
    )

    return jsonify(result), 200


@quotes_bp.get("/quotes/<int:quote_id>")
def get_quote(quote_id):
    """
    GET /api/quotes/<quote_id>
    """

    result = QuoteService.get_quote(
        quote_id
    )

    if result is None:
        return jsonify(
            {
                "error": "Quote not found"
            }
        ), 404

    return jsonify(result), 200

@quotes_bp.post("/quotes")
def create_quote():

    quote = QuoteService.create_quote(request.json)

    return jsonify({
        "success": True,
        "message": "Quote created successfully",
        "data": quote,
    }), 201