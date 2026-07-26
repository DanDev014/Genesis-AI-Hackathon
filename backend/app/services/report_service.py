from datetime import datetime, timedelta, timezone

from sqlalchemy import func

from app.extensions import db
from app.models.client import Client
from app.models.proposal import Proposal
from app.models.quote import Quote
from app.models.summary import Summary


class ReportService:
    """Deterministic SQL aggregates for the dashboard — no AI calls, just
    counts and sums over what's actually in the database."""

    @staticmethod
    def get_dashboard():
        """
        GET /api/dashboard
        """

        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)

        # ------------------------------------------------------------
        # Headline metrics
        # ------------------------------------------------------------
        total_clients = Client.query.count()
        clients_this_month = Client.query.filter(
            Client.created_at >= thirty_days_ago
        ).count()

        meetings_processed = Summary.query.count()

        proposals_in_review = Proposal.query.filter(
            Proposal.status == "sent"
        ).count()

        pipeline_value = (
            db.session.query(func.coalesce(func.sum(Quote.total_amount), 0))
            .join(Proposal, Quote.proposal_id == Proposal.proposal_id)
            .filter(Proposal.status.in_(["draft", "sent", "revised"]))
            .scalar()
        )

        # Win rate is the actual deal outcome (Proposal.outcome), not a
        # quote's own document status — a quote can sit "accepted" long
        # after the deal itself was lost, or never get marked at all.
        won_proposals = Proposal.query.filter(Proposal.outcome == "won").count()
        decided_proposals = Proposal.query.filter(
            Proposal.outcome.in_(["won", "lost"])
        ).count()
        win_rate = round((won_proposals / decided_proposals) * 100) if decided_proposals else 0

        # Meeting -> delivered-proposal turnaround. Only counts proposals
        # that actually have a meeting_occurred_at — proposals created
        # outside the transcript-extraction flow (or before this column
        # existed) have no signal for this and are excluded, not treated
        # as zero.
        avg_time_to_proposal_seconds = (
            db.session.query(
                func.avg(func.extract("epoch", Proposal.created_at - Proposal.meeting_occurred_at))
            )
            .filter(Proposal.meeting_occurred_at.isnot(None))
            .scalar()
        )
        avg_time_to_proposal_hours = (
            round(avg_time_to_proposal_seconds / 3600, 1)
            if avg_time_to_proposal_seconds is not None
            else None
        )

        # ------------------------------------------------------------
        # Pipeline by proposal status
        # ------------------------------------------------------------
        status_order = ["draft", "sent", "revised", "accepted", "rejected"]
        status_counts = dict(
            db.session.query(Proposal.status, func.count(Proposal.proposal_id))
            .group_by(Proposal.status)
            .all()
        )
        pipeline = [
            {"label": label.capitalize(), "count": status_counts.get(label, 0)}
            for label in status_order
            if status_counts.get(label, 0) > 0
        ]

        # ------------------------------------------------------------
        # Recent activity — latest clients, proposals, quotes, summaries
        # merged into one feed by created_at.
        # ------------------------------------------------------------
        activity = []

        for client in Client.query.order_by(Client.created_at.desc()).limit(5):
            activity.append({
                "id": f"client-{client.client_id}",
                "client": client.name,
                "company": client.company,
                "activity": "New client added",
                "status": client.status or "New",
                "created_at": client.created_at.isoformat() if client.created_at else None,
            })

        for proposal in Proposal.query.order_by(Proposal.created_at.desc()).limit(5):
            activity.append({
                "id": f"proposal-{proposal.proposal_id}",
                "client": proposal.client.name if proposal.client else "—",
                "company": proposal.client.company if proposal.client else "—",
                "activity": "Proposal created",
                "status": proposal.status,
                "created_at": proposal.created_at.isoformat() if proposal.created_at else None,
            })

        for quote in Quote.query.order_by(Quote.created_at.desc()).limit(5):
            client = quote.proposal.client if quote.proposal else None
            activity.append({
                "id": f"quote-{quote.quote_id}",
                "client": client.name if client else "—",
                "company": client.company if client else "—",
                "activity": "Quotation created",
                "status": quote.status,
                "created_at": quote.created_at.isoformat() if quote.created_at else None,
            })

        for summary in Summary.query.order_by(Summary.created_at.desc()).limit(5):
            activity.append({
                "id": f"summary-{summary.summary_id}",
                "client": summary.client.name if summary.client else "—",
                "company": summary.client.company if summary.client else "—",
                "activity": "Meeting summary processed",
                "status": "Processed",
                "created_at": summary.created_at.isoformat() if summary.created_at else None,
            })

        activity.sort(key=lambda a: a["created_at"] or "", reverse=True)

        return {
            "success": True,
            "data": {
                "metrics": {
                    "total_clients": total_clients,
                    "clients_this_month": clients_this_month,
                    "meetings_processed": meetings_processed,
                    "proposals_in_review": proposals_in_review,
                    "pipeline_value": float(pipeline_value or 0),
                    "win_rate": win_rate,
                    "avg_time_to_proposal_hours": avg_time_to_proposal_hours,
                },
                "pipeline": pipeline,
                "recent_activity": activity[:8],
            },
        }
