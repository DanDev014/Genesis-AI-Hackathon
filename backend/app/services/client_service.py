from sqlalchemy import asc, desc, or_

from app.extensions import db
from app.exceptions import (
    ConflictError,
    DatabaseError,
    ResourceNotFound,
    ValidationError,
)
from app.models.client import Client


class ClientService:

    @staticmethod
    def list_clients(params):
        """
        GET /api/clients
        """

        query = Client.query

        # ------------------------
        # Search
        # ------------------------
        search = params.get("search")
        if search:
            query = query.filter(
                or_(
                    Client.name.ilike(f"%{search}%"),
                    Client.company.ilike(f"%{search}%"),
                )
            )

        # ------------------------
        # Filters
        # ------------------------
        status = params.get("status")
        if status:
            query = query.filter(
                Client.status == status
            )

        industry = params.get("industry")
        if industry:
            query = query.filter(
                Client.industry == industry
            )

        manager_id = params.get("manager_id")
        if manager_id:
            query = query.filter(
                Client.assigned_account_manager == manager_id
            )

        # ------------------------
        # Sorting
        # ------------------------
        sort = params.get(
            "sort",
            "-created_at",
        )

        if sort.startswith("-"):
            column = getattr(
                Client,
                sort[1:],
                Client.created_at,
            )
            query = query.order_by(
                desc(column)
            )
        else:
            column = getattr(
                Client,
                sort,
                Client.created_at,
            )
            query = query.order_by(
                asc(column)
            )

        # ------------------------
        # Pagination
        # ------------------------
        try:
            page = int(
                params.get("page", 1)
            )
            limit = int(
                params.get("limit", 20)
            )
        except ValueError:
            raise ValidationError(
                "page and limit must be integers."
            )

        pagination = query.paginate(
            page=page,
            per_page=limit,
            error_out=False,
        )

        return {
            "success": True,
            "data": [
                client.to_dict()
                for client in pagination.items
            ],
            "meta": {
                "page": pagination.page,
                "limit": pagination.per_page,
                "total": pagination.total,
                "pages": pagination.pages,
            },
        }

    @staticmethod
    def get_client(client_id):
        """
        GET /api/clients/<id>
        """

        client = db.session.get(
            Client,
            client_id,
        )

        if client is None:
            raise ResourceNotFound(
                "Client not found."
            )

        return {
            "success": True,
            "data": client.to_dict(),
        }

    @staticmethod
    def create_client(data):
        """
        POST /api/clients
        """

        if not data:
            raise ValidationError(
                "Request body is required."
            )

        required_fields = [
            "user_id",
            "name",
            "company",
            "industry",
            "email",
        ]

        for field in required_fields:
            value = data.get(field)

            if value is None or (
                isinstance(value, str)
                and not value.strip()
            ):
                raise ValidationError(
                    f"{field} is required."
                )

        existing_client = Client.query.filter_by(
            email=data["email"]
        ).first()

        if existing_client:
            raise ConflictError(
                "A client with this email already exists."
            )

        try:

            client = Client(
                user_id=data["user_id"],
                name=data["name"],
                company=data["company"],
                industry=data["industry"],
                phone=data.get("phone"),
                email=data["email"],
                source=data.get("source"),
                status=data.get(
                    "status",
                    "lead",
                ),
                assigned_account_manager=data.get(
                    "assigned_account_manager"
                ),
            )

            db.session.add(client)
            db.session.commit()

            return {
                "success": True,
                "message": (
                    "Client created successfully."
                ),
                "data": client.to_dict(),
            }

        except Exception:
            db.session.rollback()

            raise DatabaseError(
                "Unable to create client."
            )