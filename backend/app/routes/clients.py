from flask import Blueprint, jsonify, request

from app.services.client_service import ClientService

clients_bp = Blueprint("clients", __name__)


@clients_bp.get("/clients")
def list_clients():

    result = ClientService.list_clients(request.args)

    return jsonify(result), 200


@clients_bp.get("/clients/<int:client_id>")
def get_client(client_id):

    result = ClientService.get_client(client_id)

    if result is None:
        return jsonify(
            {
                "error": "Client not found"
            }
        ), 404

    return jsonify(result), 200