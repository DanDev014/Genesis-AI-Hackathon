from flask import Blueprint, jsonify, request

from app.exceptions import ResourceNotFound
from app.services.client_service import ClientService

clients_bp = Blueprint(
    "clients",
    __name__,
)


@clients_bp.get("/clients")
def list_clients():
    """
    GET /api/clients

    Query Params
    ------------
    search
    status
    industry
    manager_id
    page
    limit
    sort
    """

    result = ClientService.list_clients(request.args)

    return jsonify(result), 200


@clients_bp.get("/clients/<int:client_id>")
def get_client(client_id):
    """
    GET /api/clients/<id>
    """

    client = ClientService.get_client(client_id)

    if not client:
        raise ResourceNotFound("Client not found")

    return jsonify(client), 200


@clients_bp.post("/clients")
def create_client():
    """
    POST /api/clients
    """

    data = request.get_json(silent=True) or {}

    client = ClientService.create_client(data)

    return jsonify(client), 201