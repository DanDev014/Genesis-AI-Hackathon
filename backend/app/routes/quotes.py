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


@quotes_bp.patch("/quotes/<int:quote_id>")
def update_quote(quote_id):
    """
    PATCH /api/quotes/<id>
    """

    quote = QuoteService.update_quote(
        quote_id, request.get_json(silent=True)
    )

    return jsonify({
        "success": True,
        "message": "Quote updated successfully",
        "data": quote,
    }), 200


@quotes_bp.post("/quotes/<int:quote_id>/send-to-quickbooks")
def send_to_quickbooks(quote_id):
    """
    POST /api/quotes/<id>/send-to-quickbooks

    Body: { user_id? }

    412-equivalent (409 Conflict) if the linked proposal hasn't been
    approved yet.
    """

    quote = QuoteService.send_to_quickbooks(
        quote_id, request.get_json(silent=True)
    )

    return jsonify({
        "success": True,
        "message": "Sent to QuickBooks",
        "data": quote,
    }), 200