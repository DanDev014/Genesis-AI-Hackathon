import secrets
from datetime import datetime

from sqlalchemy import asc, desc

from app.models.proposal import Proposal
from app.models.activity_log import ActivityLog
from app.extensions import db
from app.exceptions import (
    DatabaseError,
    ResourceNotFound,
    ValidationError,
)
from app.services.email_service import send_email
from app.services.webhook_dispatcher import dispatch_event
from app.services.activity_log_service import ActivityLogService
from app.utils.constants import PROPOSAL_OUTCOMES

# Fields an AI draft actually writes — used to detect (and log) a human
# correcting one of them, which is the raw signal the AI feedback loop
# feeds back into future extractions.
_AI_DRAFT_FIELDS = ("scope_of_work", "deliverables_list", "timeline_milestones")


class ProposalService:

    @staticmethod
    def _normalize_requirements(items):
        """Accept either a list of plain strings (fresh from extraction) or
        {"text", "checked"} dicts (round-tripped from a previous save), and
        return the checklist shape consistently either way."""
        normalized = []
        for item in items or []:
            if isinstance(item, dict):
                text = (item.get("text") or "").strip()
                checked = bool(item.get("checked", False))
            else:
                text = str(item).strip()
                checked = False
            if text:
                normalized.append({"text": text, "checked": checked})
        return normalized

    @staticmethod
    def _parse_meeting_time(value):
        """Best-effort ISO string -> naive UTC datetime. None (not an
        error) if unparseable or absent — meeting_occurred_at is always
        optional, callers without a real signal just don't set it."""
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            return parsed.replace(tzinfo=None) if parsed.tzinfo else parsed
        except (ValueError, TypeError):
            return None

    @staticmethod
    def list_proposals(params):

        query = Proposal.query

        # ------------------------
        # Filters
        # ------------------------
        client_id = params.get("client_id")
        if client_id:
            query = query.filter(
                Proposal.client_id == client_id
            )

        status = params.get("status")
        if status:
            query = query.filter(
                Proposal.status == status
            )

        generated_by = params.get("generated_by")
        if generated_by:
            query = query.filter(
                Proposal.generated_by == generated_by
            )

        # ------------------------
        # Sorting
        # ------------------------
        sort = params.get("sort", "-created_at")

        if sort.startswith("-"):
            column = getattr(
                Proposal,
                sort[1:],
                Proposal.created_at,
            )
            query = query.order_by(desc(column))
        else:
            column = getattr(
                Proposal,
                sort,
                Proposal.created_at,
            )
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
                proposal.to_dict()
                for proposal in pagination.items
            ],
            "meta": {
                "page": page,
                "limit": limit,
                "total": pagination.total,
                "pages": pagination.pages,
            },
        }

    @staticmethod
    def get_proposal(proposal_id):

        proposal = Proposal.query.get(proposal_id)

        if not proposal:
            return None

        return proposal.to_dict()


    @staticmethod
    def create_proposal(data):

        proposal = Proposal(
            client_id=data["client_id"],

            created_by_user_id=data["user_id"],

            linked_transcript_id=data.get("transcript_id"),

            scope_of_work=data["scope_of_work"],

            deliverables_list=data["deliverables_list"],

            requirements_checklist=ProposalService._normalize_requirements(
                data.get("requirements_checklist") or data.get("requirements")
            ),

            timeline_milestones=data["timeline_milestones"],

            meeting_occurred_at=ProposalService._parse_meeting_time(
                data.get("meeting_occurred_at")
            ),

            generated_by=data.get("generated_by", "ai"),

            status=data.get("status", "draft"),

            # Generated immediately, not just on first "Send" — the share
            # link exists the moment a draft does, so a human never has to
            # click Send purely to get a link to hand someone.
            share_token=secrets.token_urlsafe(24),
        )

        db.session.add(proposal)
        db.session.flush()  # assigns proposal.proposal_id for the log row below

        ActivityLogService.record(
            "proposal", proposal.proposal_id, "created",
            user_id=data.get("user_id"),
            details={"generated_by": proposal.generated_by},
        )

        db.session.commit()

        result = proposal.to_dict()

        # No human clicked Send — this is the team-facing notification that
        # a draft exists and is ready for someone to review/send, standing
        # in for "the client link sends itself" without skipping human
        # review of an AI-guessed scope/price before it reaches a client.
        dispatch_event("proposal.draft_ready", result)

        return result

    @staticmethod
    def update_proposal(proposal_id, data):
        """
        PATCH /api/proposals/<id>

        Lets a manager revise a draft before approving it. Only touches
        fields actually present in the body — a PATCH, not a full replace.
        """

        if not data:
            raise ValidationError(
                "Request body is required"
            )

        proposal = Proposal.query.get(proposal_id)

        if proposal is None:
            raise ResourceNotFound("Proposal not found")

        # Snapshot before mutating — this is the actual signal the AI
        # feedback loop uses: what a human corrected on an AI-drafted field.
        is_ai_draft = "ai" in (proposal.generated_by or "").lower()
        changes = {}
        for field in _AI_DRAFT_FIELDS:
            if field in data and getattr(proposal, field) != data[field]:
                changes[field] = {"before": getattr(proposal, field), "after": data[field]}

        if "scope_of_work" in data:
            proposal.scope_of_work = data["scope_of_work"]

        if "deliverables_list" in data:
            proposal.deliverables_list = data["deliverables_list"]

        if "requirements_checklist" in data:
            proposal.requirements_checklist = ProposalService._normalize_requirements(
                data["requirements_checklist"]
            )

        if "timeline_milestones" in data:
            proposal.timeline_milestones = data["timeline_milestones"]

        if "status" in data:
            proposal.status = data["status"]

        if "version" in data:
            proposal.version = data["version"]

        if changes:
            ActivityLogService.record(
                "proposal", proposal.proposal_id, "updated",
                user_id=data.get("user_id"),
                details={"changes": changes, "is_ai_edit": is_ai_draft},
            )

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()

            raise DatabaseError(
                "Unable to update proposal."
            )

        return proposal.to_dict()

    @staticmethod
    def get_activity(proposal_id):
        """GET /api/proposals/<id>/activity — user-attributed event log,
        newest first."""
        return [log.to_dict() for log in ActivityLogService.list_for("proposal", proposal_id)]

    @staticmethod
    def feedback_examples(limit=3):
        """The AI feedback loop's actual data source: recent resolved
        (won/lost) AI-drafted proposals, each paired with the earliest
        human edit made to it (if any). genesis_agent fetches this and
        feeds it back into the extraction prompt as few-shot context —
        not model fine-tuning, just "here's what the team corrected and
        what happened" for the LLM to weigh."""
        proposals = (
            Proposal.query
            .filter(Proposal.outcome.in_(["won", "lost"]))
            .filter(Proposal.generated_by.ilike("%ai%"))
            .order_by(Proposal.outcome_at.desc())
            .limit(limit)
            .all()
        )

        examples = []
        for proposal in proposals:
            edit_log = (
                ActivityLog.query
                .filter_by(entity_type="proposal", entity_id=proposal.proposal_id, action="updated")
                .order_by(ActivityLog.created_at.asc())
                .first()
            )
            examples.append({
                "scope_of_work": proposal.scope_of_work,
                "deliverables": proposal.deliverables_list,
                "timeline": proposal.timeline_milestones,
                "outcome": proposal.outcome,
                "outcome_notes": proposal.outcome_notes,
                "human_edit": (edit_log.details or {}).get("changes") if edit_log else None,
            })
        return examples

    @staticmethod
    def get_public_proposal(token):
        """Look up a proposal by its unguessable share token — this, not a
        JWT, is the access boundary for the client-facing /p/<token> page."""

        if not token:
            return None

        proposal = Proposal.query.filter_by(share_token=token).first()

        if not proposal:
            return None

        return proposal.to_public_dict()

    @staticmethod
    def send_proposal(proposal_id, data):
        """
        POST /api/proposals/<id>/send

        Generates the share link (once, reused on every subsequent send),
        emails it to the given address, and marks the proposal as sent.
        """
        from flask import current_app

        if not data or not (data.get("to_email") or "").strip():
            raise ValidationError("Recipient email is required")

        proposal = Proposal.query.get(proposal_id)

        if proposal is None:
            raise ResourceNotFound("Proposal not found")

        if not proposal.share_token:
            proposal.share_token = secrets.token_urlsafe(24)

        share_url = f"{current_app.config.get('PUBLIC_APP_URL')}/p/{proposal.share_token}"

        company = proposal.client.company if proposal.client else "your project"
        subject = (data.get("subject") or "").strip() or f"Your proposal from Kora AI — {company}"
        message = (data.get("message") or "").strip() or (
            "Please find your proposal ready for review. Click below to view "
            "the full scope, timeline, and pricing."
        )

        # Send before committing anything — if delivery fails we don't want
        # a half-applied "sent" state sitting in the database.
        send_email(
            to_email=data["to_email"].strip(),
            subject=subject,
            heading="Your proposal is ready",
            message=message,
            cta_label="View proposal",
            cta_url=share_url,
        )

        proposal.status = "sent"
        proposal.sent_at = datetime.utcnow()

        ActivityLogService.record(
            "proposal", proposal.proposal_id, "sent",
            user_id=data.get("user_id"),
            details={"to_email": data["to_email"].strip()},
        )

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise DatabaseError("Email sent, but failed to update the proposal record.")

        result = proposal.to_dict()
        result["share_url"] = share_url

        dispatch_event("proposal.sent", {**result, "to_email": data["to_email"].strip()})

        return result

    @staticmethod
    def record_outcome(proposal_id, data):
        """
        POST /api/proposals/<id>/outcome

        Body: { outcome: "won"|"lost"|"pending", notes?: str }

        Deliberately separate from `status` (draft/sent/revised/accepted/
        rejected), which just tracks the document's own lifecycle. This is
        the actual business result of the deal, plus any client feedback —
        the thing "did we get the job" reporting needs, that a document
        status alone can't answer.
        """

        if not data or not data.get("outcome"):
            raise ValidationError("outcome is required")

        outcome = data["outcome"]
        if outcome not in PROPOSAL_OUTCOMES:
            raise ValidationError(f"outcome must be one of {PROPOSAL_OUTCOMES}")

        proposal = Proposal.query.get(proposal_id)

        if proposal is None:
            raise ResourceNotFound("Proposal not found")

        proposal.outcome = outcome
        if "notes" in data:
            proposal.outcome_notes = (data.get("notes") or "").strip()
        proposal.outcome_at = datetime.utcnow()

        ActivityLogService.record(
            "proposal", proposal.proposal_id, "outcome_recorded",
            user_id=data.get("user_id"),
            details={"outcome": outcome, "has_notes": bool(proposal.outcome_notes)},
        )

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()

            raise DatabaseError("Unable to record outcome.")

        return proposal.to_dict()

    @staticmethod
    def approve_proposal(proposal_id, data):
        """
        POST /api/proposals/<id>/approve

        Producer sign-off. One-way — no unapprove endpoint. This is the
        gate QuoteService.send_to_quickbooks checks before letting a quote
        reach QuickBooks; nothing else in this app currently depends on it.

        Note: any logged-in user can call this — there's no role check
        (e.g. "must be a producer/manager") because nothing in this backend
        enforces roles server-side yet. It's a real gate against sending
        an unreviewed AI draft, just not yet a gate against *who* reviews it.
        """

        proposal = Proposal.query.get(proposal_id)

        if proposal is None:
            raise ResourceNotFound("Proposal not found")

        if proposal.approved_at is None:
            proposal.approved_at = datetime.utcnow()
            proposal.approved_by_user_id = (data or {}).get("user_id")

            ActivityLogService.record(
                "proposal", proposal.proposal_id, "approved",
                user_id=(data or {}).get("user_id"),
            )

            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
                raise DatabaseError("Unable to approve proposal.")

        return proposal.to_dict()

    @staticmethod
    def is_approved(proposal_id):
        proposal = Proposal.query.get(proposal_id)
        return bool(proposal and proposal.approved_at is not None)