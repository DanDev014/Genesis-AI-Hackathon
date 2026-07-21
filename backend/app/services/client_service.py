from sqlalchemy import asc, desc, or_

from app.models.client import Client


class ClientService:

    @staticmethod
    def list_clients(params):
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
            query = query.filter(Client.status == status)

        industry = params.get("industry")
        if industry:
            query = query.filter(Client.industry == industry)

        manager_id = params.get("manager_id")
        if manager_id:
            query = query.filter(
                Client.assigned_account_manager == manager_id
            )

        # ------------------------
        # Sorting
        # ------------------------
        sort = params.get("sort", "-created_at")

        if sort.startswith("-"):
            column = getattr(Client, sort[1:], Client.created_at)
            query = query.order_by(desc(column))
        else:
            column = getattr(Client, sort, Client.created_at)
            query = query.order_by(asc(column))

        # ------------------------
        # Pagination
        # ------------------------
        page = int(params.get("page", 1))
        limit = int(params.get("limit", 20))

        pagination = query.paginate(
            page=page,
            per_page=limit,
            error_out=False,
        )

        return {
            "data": [
                client.to_dict()
                for client in pagination.items
            ],
            "meta": {
                "page": page,
                "limit": limit,
                "total": pagination.total,
                "pages": pagination.pages,
            },
        }

    @staticmethod
    def get_client(client_id):
        client = Client.query.get(client_id)

        if not client:
            return None

        return client.to_dict()

    @staticmethod
    def create_client(data):

        client = Client(
            user_id=data["user_id"],
            name=data["name"],
            company=data["company"],
            industry=data["industry"],
            phone=data.get("phone"),
            email=data["email"],
            source=data.get("source"),
            status=data.get("status", "lead"),
            assigned_account_manager=data.get(
                "assigned_account_manager"
            ),
        )

        from app.extensions import db

        db.session.add(client)
        db.session.commit()

        return client.to_dict()