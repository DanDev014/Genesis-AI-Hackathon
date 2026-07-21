from sqlalchemy import or_

from app.models.client import Client

from app.exceptions import ResourceNotFound


class ClientService:

    @staticmethod
    def list_clients(args):
        page = max(int(args.get("page", 1)), 1)
        limit = min(max(int(args.get("limit", 20)), 1), 100)

        search = args.get("search")
        status = args.get("status")
        industry = args.get("industry")
        manager_id = args.get("manager_id")
        sort = args.get("sort", "-created_at")

        query = Client.query

        # -----------------------------
        # Search
        # -----------------------------
        if search:
            query = query.filter(
                or_(
                    Client.name.ilike(f"%{search}%"),
                    Client.company.ilike(f"%{search}%"),
                )
            )

        # -----------------------------
        # Filters
        # -----------------------------
        if status:
            query = query.filter(Client.status == status)

        if industry:
            query = query.filter(Client.industry == industry)

        if manager_id:
            query = query.filter(
                Client.assigned_account_manager == manager_id
            )

        # -----------------------------
        # Sorting
        # -----------------------------
        if sort.startswith("-"):
            field = sort[1:]
            column = getattr(Client, field, Client.created_at)
            query = query.order_by(column.desc())
        else:
            column = getattr(Client, sort, Client.created_at)
            query = query.order_by(column.asc())

        pagination = query.paginate(
            page=page,
            per_page=limit,
            error_out=False,
        )

        clients = []

        for client in pagination.items:

            last_call = None

            if client.calls:
                latest = max(
                    client.calls,
                    key=lambda c: c.meeting_time,
                )
                last_call = latest.meeting_time.isoformat()

            manager = None

            if client.account_manager:
                manager = {
                    "staff_id": client.account_manager.staff_id,
                    "full_name": client.account_manager.full_name,
                }

            clients.append(
                {
                    "client_id": client.client_id,
                    "name": client.name,
                    "company": client.company,
                    "industry": client.industry,
                    "status": client.status,
                    "assigned_account_manager": manager,
                    "last_call_at": last_call,
                    "created_at": client.created_at.isoformat(),
                }
            )

        return {
            "data": clients,
            "meta": {
                "page": page,
                "limit": limit,
                "total": pagination.total,
            },
        }

    @staticmethod
    def get_client(client_id):

        client = Client.query.get(client_id)

        if client is None:
            raise ResourceNotFound("Client not found")

        manager = None

        if client.account_manager:
            manager = {
                "staff_id": client.account_manager.staff_id,
                "full_name": client.account_manager.full_name,
            }

        calls = []

        for call in client.calls:

            transcript = None

            if call.transcript:
                transcript = {
                    "transcript_id": call.transcript.transcript_id,
                    "summary": call.transcript.summary,
                    "confidence_score": (
                        float(call.transcript.confidence_score)
                        if call.transcript.confidence_score
                        else None
                    ),
                }

            calls.append(
                {
                    "call_id": call.call_id,
                    "meeting_time": call.meeting_time.isoformat(),
                    "duration_minutes": call.duration_minutes,
                    "call_type": call.call_type,
                    "recording_url": call.recording_url,
                    "transcript": transcript,
                }
            )

        proposals = []

        for proposal in client.proposals:

            proposals.append(
                {
                    "proposal_id": proposal.proposal_id,
                    "version": proposal.version,
                    "status": proposal.status,
                }
            )

        stats = {
            "total_calls": len(client.calls),
            "total_proposals": len(client.proposals),
        }

        return {
            "client_id": client.client_id,
            "name": client.name,
            "company": client.company,
            "industry": client.industry,
            "status": client.status,
            "email": client.email,
            "phone": client.phone,
            "source": client.source,
            "assigned_account_manager": manager,
            "created_at": client.created_at.isoformat(),
            "stats": stats,
            "calls": calls,
            "proposals": proposals,
        }