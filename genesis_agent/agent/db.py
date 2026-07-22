"""
Postgres integration for Kora.

Reads DATABASE_URL from .env. If set and reachable, everything reads and
writes go here. If not, Kora silently falls back to file storage so the
demo can't die from a bad connection.

Schema (from Genesis):
  users, team_members, clients, call_records, transcripts,
  proposals, quotes, proposal_activity_log, project_briefs

The schema has NOT NULL columns Kora doesn't always produce (email,
industry, duration_minutes, etc). We fill safe defaults BEFORE writing
so DB constraints don't reject valid Kora records. Every default is
documented in the code so it's easy to audit.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from typing import Any, List, Optional

DATABASE_URL = os.getenv("DATABASE_URL", "")


def _normalize_url(url: str) -> str:
    """Accept whichever prefix the Neon UI copies; ensure SSL is required."""
    if not url:
        return url
    if url.startswith("postgresql+psycopg://"):
        url = url.replace("postgresql+psycopg://", "postgresql://", 1)
    elif url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    if "sslmode=" not in url:
        url += ("&" if "?" in url else "?") + "sslmode=require"
    return url


DATABASE_URL = _normalize_url(DATABASE_URL)

_pool = None
_available: bool = False
_last_error: Optional[str] = None


def is_available() -> bool:
    return _available


def last_error() -> Optional[str]:
    return _last_error


def status() -> dict:
    return {
        "configured": bool(DATABASE_URL),
        "available": _available,
        "last_error": _last_error,
        "url_redacted": re.sub(r"://([^:]+):([^@]+)@", r"://\1:****@", DATABASE_URL or ""),
    }


def init() -> None:
    global _pool, _available, _last_error
    if not DATABASE_URL:
        _last_error = "DATABASE_URL not set — using file store."
        return
    try:
        from psycopg_pool import ConnectionPool  # type: ignore
        _pool = ConnectionPool(
            conninfo=DATABASE_URL,
            min_size=1, max_size=4,
            open=True, kwargs={"autocommit": True},
            # Neon drops idle connections; without this, a stale pooled
            # connection gets handed out, the query fails, and every write
            # silently falls back to file storage for that request.
            check=ConnectionPool.check_connection,
        )
        with _pool.connection() as conn, conn.cursor() as cur:
            cur.execute("select 1")
            cur.fetchone()
        _available = True
        _last_error = None
        print(f"[db] connected to Postgres: {status()['url_redacted']}")
        _ensure_extras()
    except Exception as exc:
        _pool = None
        _available = False
        _last_error = f"{type(exc).__name__}: {exc}"
        print(f"[db] connection FAILED, falling back to file store — {_last_error}")


def close() -> None:
    global _pool
    if _pool is not None:
        try:
            _pool.close()
        except Exception:
            pass
        _pool = None


def _rows(sql: str, args: tuple = ()) -> List[dict]:
    if not _available or _pool is None:
        return []
    with _pool.connection() as conn, conn.cursor() as cur:
        cur.execute(sql, args)
        cols = [d[0] for d in cur.description or []]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


def _one(sql: str, args: tuple = ()) -> Optional[dict]:
    rs = _rows(sql, args)
    return rs[0] if rs else None


def _exec(sql: str, args: tuple = ()) -> Any:
    if not _available or _pool is None:
        return None
    with _pool.connection() as conn, conn.cursor() as cur:
        cur.execute(sql, args)
        if cur.description:
            cols = [d[0] for d in cur.description]
            row = cur.fetchone()
            return dict(zip(cols, row)) if row else None
        return None


# --------------------------------------------------------------------------
# Bootstrap tables that aren't in Genesis's DDL but Kora needs.
# We only add tables, never modify Genesis's. Safe to re-run.
# --------------------------------------------------------------------------
def _ensure_extras() -> None:
    """Create Kora-specific tables that ride alongside Genesis's schema."""
    with _pool.connection() as conn, conn.cursor() as cur:
        cur.execute("""
            create table if not exists project_briefs (
                brief_id       serial primary key,
                client_id      integer,
                transcript_id  integer,
                content        text not null,
                clarity_score  numeric(4, 1),
                status         varchar(20) default 'draft'
                                 check (status in ('draft', 'approved', 'archived')),
                version        integer default 1,
                approved_by    integer,
                approved_at    timestamptz,
                meeting_type   varchar(20) default 'discovery_call',
                created_at     timestamptz default current_timestamp
            )
        """)
        # Older deployments created the table before meeting_type existed.
        cur.execute("""
            alter table project_briefs
              add column if not exists meeting_type varchar(20) default 'discovery_call'
        """)


# --------------------------------------------------------------------------
# Client resolution — schema forces email UNIQUE NOT NULL + industry NOT NULL
# --------------------------------------------------------------------------
def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (s or "").lower()).strip("_") or "unknown"


def _client_id_for(company: str, name: str, email: str = "") -> Optional[int]:
    if not company and not name:
        return None

    if email:
        row = _one("select client_id from clients where email = %s", (email,))
        if row:
            return row["client_id"]
    row = _one("select client_id from clients where company = %s", (company or name,))
    if row:
        return row["client_id"]

    # Synth defaults to satisfy NOT NULL / UNIQUE constraints.
    synth_email = email or f"{_slug(company or name)}@unknown.local"
    row = _exec(
        """
        insert into clients (client_id, name, company, industry, email, source, status, created_at)
        values ((select coalesce(max(client_id), 0) + 1 from clients), %s, %s, %s, %s, %s, %s, %s)
        on conflict (email) do update set company = excluded.company
        returning client_id
        """,
        (
            name or company or "Unknown",
            company or name or "Unknown",
            "Unknown",              # industry — NOT NULL, we synthesise
            synth_email,             # UNIQUE NOT NULL
            "inbound form",          # allowed by clients_source_check
            "lead",                  # allowed by clients_status_check
            datetime.now(timezone.utc),
        ),
    )
    return row["client_id"] if row else None


def _int(s: str) -> Optional[int]:
    try:
        return int(s)
    except (TypeError, ValueError):
        return None


# --------------------------------------------------------------------------
# Proposals
# --------------------------------------------------------------------------
def save_proposal(data: dict) -> dict:
    client_id = _client_id_for(
        data.get("client_company", ""),
        data.get("client_name", ""),
        data.get("client_email", ""),
    )
    if not client_id:
        raise RuntimeError("Cannot save proposal — need client_company or client_name.")

    row = _exec(
        """
        insert into proposals
          (client_id, scope_of_work, deliverables_list, timeline_milestones,
           version, status, generated_by, created_at)
        values (%s, %s, %s::jsonb, %s::jsonb, %s, %s, %s, %s)
        returning proposal_id, created_at
        """,
        (
            client_id,
            data.get("scope") or data.get("summary") or data.get("title", ""),
            json.dumps(data.get("deliverables", [])),
            json.dumps(_timeline_json(data)),
            int(data.get("version", 1)),
            data.get("status", "draft"),
            "AI-drafted",           # allowed by proposals_generated_by_check
            datetime.now(timezone.utc),
        ),
    )
    proposal_id = row["proposal_id"]
    log_activity(proposal_id, "generated", notes=data.get("title", ""))
    data = dict(data)
    data["id"] = str(proposal_id)
    data["number"] = f"{proposal_id:04d}"
    data["created_at"] = row["created_at"].isoformat()
    return data


def list_proposals() -> List[dict]:
    rows = _rows("""
        select p.proposal_id, p.status, p.version, p.generated_by, p.created_at,
               p.scope_of_work, p.deliverables_list,
               c.name as client_name, c.company as client_company
        from proposals p
        left join clients c on c.client_id = p.client_id
        order by p.proposal_id desc
        limit 100
    """)
    return [_proposal_row_to_kora(r) for r in rows]


def get_proposal(doc_id: str) -> Optional[dict]:
    pid = _int(doc_id)
    if pid is None:
        return None
    r = _one("""
        select p.*, c.name as client_name, c.company as client_company
        from proposals p left join clients c on c.client_id = p.client_id
        where p.proposal_id = %s
    """, (pid,))
    return _proposal_row_to_kora(r) if r else None


def update_proposal(doc_id: str, patch: dict) -> Optional[dict]:
    """Apply a partial update. 'status' drives the approval workflow; the
    rest (scope/deliverables/timeline) let a manager revise a draft before
    approving it — logged as a single 'edited' activity entry, distinct
    from the status-change entry so the audit trail reads clearly."""
    pid = _int(doc_id)
    if pid is None:
        return None
    if "status" in patch:
        _exec("update proposals set status = %s where proposal_id = %s",
              (patch["status"], pid))
        log_activity(pid, _status_to_action(patch["status"]), notes=patch.get("notes", ""))
    if "scope" in patch:
        _exec("update proposals set scope_of_work = %s where proposal_id = %s",
              (patch["scope"], pid))
    if "deliverables" in patch:
        _exec("update proposals set deliverables_list = %s::jsonb where proposal_id = %s",
              (json.dumps(patch["deliverables"]), pid))
    if "timeline" in patch:
        _exec("update proposals set timeline_milestones = %s::jsonb where proposal_id = %s",
              (json.dumps(_timeline_json(patch)), pid))
    if any(k in patch for k in ("scope", "deliverables", "timeline")):
        log_activity(pid, "edited", notes=patch.get("notes", "Manager edit"))
    return get_proposal(doc_id)


def _status_to_action(status: str) -> str:
    """Map a status change to an audit action that satisfies the check constraint."""
    return {
        "sent": "sent",
        "accepted": "accepted",
        "approved": "approved",
        "internal_review": "edited",
        "revised": "edited",
        "rejected": "changes_requested",
    }.get(status, "edited")


# --------------------------------------------------------------------------
# Proposal activity log — needed for the approval gate
# --------------------------------------------------------------------------
def log_activity(proposal_id: int, action: str, notes: str = "",
                 actor_user_id: Optional[int] = None) -> None:
    """Append to proposal_activity_log. Actions must match the check constraint.

    activity_id has no default/identity/sequence in Genesis's schema, so we
    assign the next id ourselves rather than altering their table."""
    _exec("""
        insert into proposal_activity_log
          (activity_id, proposal_id, actor_user_id, action, notes, created_at)
        values (
          (select coalesce(max(activity_id), 0) + 1 from proposal_activity_log),
          %s, %s, %s, %s, %s)
    """, (proposal_id, actor_user_id, action, notes[:500],
          datetime.now(timezone.utc)))


def proposal_history(proposal_id: int) -> List[dict]:
    return _rows("""
        select activity_id, action, notes, created_at
        from proposal_activity_log
        where proposal_id = %s
        order by activity_id desc
    """, (proposal_id,))


def proposal_is_approved(proposal_id: int) -> bool:
    """True if we've ever recorded an 'approved' action on this proposal."""
    r = _one("""
        select 1 from proposal_activity_log
        where proposal_id = %s and action = 'approved' limit 1
    """, (proposal_id,))
    return r is not None


# --------------------------------------------------------------------------
# Quotes
# --------------------------------------------------------------------------
def save_quote(data: dict) -> dict:
    for it in data.get("line_items", []):
        it.setdefault("qty", 1)
        it.setdefault("unit_price", 0)
        it["amount"] = it.get("amount") or round(it["qty"] * it["unit_price"], 2)
    subtotal = round(sum(i["amount"] for i in data.get("line_items", [])), 2)
    data.setdefault("subtotal", subtotal)
    data.setdefault("total", subtotal)
    data.setdefault("currency", data.get("currency", "KES"))

    # Quotes must reference a proposal (NOT NULL FK). Mint a stub if needed.
    proposal_id = _int(str(data.get("proposal_id", ""))) if data.get("proposal_id") else None
    if proposal_id is None:
        stub = save_proposal({
            "client_company": data.get("client_company", ""),
            "client_name": data.get("client_name", ""),
            "client_email": data.get("client_email", ""),
            "title": data.get("title", ""),
            "scope": data.get("title", ""),
            "deliverables": [i.get("item", "") for i in data.get("line_items", [])],
            "status": "draft",
        })
        proposal_id = int(stub["id"])

    row = _exec("""
        insert into quotes
          (proposal_id, currency, tax_rate, discount_amount, total_amount,
           validity_days, status, line_items, created_at)
        values (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s)
        returning quote_id, created_at
    """, (
        proposal_id,
        (data.get("currency") or "KES")[:5],
        float(data.get("tax_rate", 16.00)),
        float(data.get("discount_amount", 0)),
        float(data.get("total", 0)),
        int(data.get("valid_days", 30)),
        data.get("status", "draft"),
        json.dumps(data.get("line_items", [])),
        datetime.now(timezone.utc),
    ))
    data = dict(data)
    data["id"] = str(row["quote_id"])
    data["number"] = f"{row['quote_id']:04d}"
    data["proposal_id"] = proposal_id
    data["created_at"] = row["created_at"].isoformat()
    return data


def list_quotes() -> List[dict]:
    rows = _rows("""
        select q.quote_id, q.proposal_id, q.currency, q.tax_rate, q.discount_amount,
               q.total_amount, q.status, q.line_items, q.created_at,
               p.scope_of_work,
               c.name as client_name, c.company as client_company
        from quotes q
        left join proposals p on p.proposal_id = q.proposal_id
        left join clients c on c.client_id = p.client_id
        order by q.quote_id desc
        limit 100
    """)
    return [_quote_row_to_kora(r) for r in rows]


def get_quote(doc_id: str) -> Optional[dict]:
    qid = _int(doc_id)
    if qid is None:
        return None
    r = _one("""
        select q.*, p.scope_of_work,
               c.name as client_name, c.company as client_company
        from quotes q
        left join proposals p on p.proposal_id = q.proposal_id
        left join clients c on c.client_id = p.client_id
        where q.quote_id = %s
    """, (qid,))
    return _quote_row_to_kora(r) if r else None


def update_quote(doc_id: str, patch: dict) -> Optional[dict]:
    """Apply a partial update. line_items also recomputes total_amount so a
    manager's pricing edit stays consistent with what gets quoted."""
    qid = _int(doc_id)
    if qid is None:
        return None
    if "status" in patch:
        _exec("update quotes set status = %s where quote_id = %s",
              (patch["status"], qid))
    if "line_items" in patch:
        items = []
        for it in patch["line_items"]:
            it = dict(it)
            it.setdefault("qty", 1)
            it.setdefault("unit_price", 0)
            it["amount"] = it.get("amount") or round(it["qty"] * it["unit_price"], 2)
            items.append(it)
        total = round(sum(i["amount"] for i in items), 2)
        _exec("update quotes set line_items = %s::jsonb, total_amount = %s where quote_id = %s",
              (json.dumps(items), total, qid))
    if "tax_rate" in patch:
        _exec("update quotes set tax_rate = %s where quote_id = %s", (float(patch["tax_rate"]), qid))
    if "discount_amount" in patch:
        _exec("update quotes set discount_amount = %s where quote_id = %s",
              (float(patch["discount_amount"]), qid))
    if "currency" in patch:
        _exec("update quotes set currency = %s where quote_id = %s", (patch["currency"][:5], qid))
    if "validity_days" in patch:
        _exec("update quotes set validity_days = %s where quote_id = %s",
              (int(patch["validity_days"]), qid))
    if "quickbooks" in patch:
        r = _one("select line_items from quotes where quote_id = %s", (qid,))
        if r:
            existing = r["line_items"]
            if isinstance(existing, str):
                existing = json.loads(existing or "[]")
            # Unwrap if already wrapped.
            items = existing.get("items") if isinstance(existing, dict) else existing
            wrapper = {"items": items or [], "quickbooks": patch["quickbooks"]}
            _exec("update quotes set line_items = %s::jsonb where quote_id = %s",
                  (json.dumps(wrapper), qid))
    return get_quote(doc_id)


# --------------------------------------------------------------------------
# Project briefs — the missing artifact between capture and proposal
# --------------------------------------------------------------------------
def save_brief(client_company: str, client_name: str, content: str,
               clarity_score: Optional[float] = None,
               transcript_id: Optional[int] = None,
               meeting_type: str = "discovery_call") -> dict:
    client_id = _client_id_for(client_company, client_name, "")
    if not client_id:
        raise RuntimeError("Cannot save brief — need client_company or client_name.")
    row = _exec("""
        insert into project_briefs
          (client_id, transcript_id, content, clarity_score, status, version, meeting_type, created_at)
        values (%s, %s, %s, %s, 'draft', 1, %s, %s)
        returning brief_id, created_at
    """, (client_id, transcript_id, content, clarity_score, meeting_type,
          datetime.now(timezone.utc)))
    return {
        "id": str(row["brief_id"]),
        "brief_id": row["brief_id"],
        "client_id": client_id,
        "content": content,
        "clarity_score": clarity_score,
        "status": "draft",
        "meeting_type": meeting_type,
        "created_at": row["created_at"].isoformat(),
    }


def list_briefs() -> List[dict]:
    rows = _rows("""
        select b.brief_id, b.content, b.clarity_score, b.status, b.created_at,
               b.approved_at, b.meeting_type, c.company as client_company, c.name as client_name
        from project_briefs b
        left join clients c on c.client_id = b.client_id
        order by b.brief_id desc
        limit 100
    """)
    return [_brief_row(r) for r in rows]


def get_brief(brief_id: str) -> Optional[dict]:
    bid = _int(brief_id)
    if bid is None:
        return None
    r = _one("""
        select b.*, c.company as client_company, c.name as client_name
        from project_briefs b
        left join clients c on c.client_id = b.client_id
        where b.brief_id = %s
    """, (bid,))
    return _brief_row(r) if r else None


def approve_brief(brief_id: str, approver: Optional[int] = None) -> Optional[dict]:
    bid = _int(brief_id)
    if bid is None:
        return None
    _exec("""
        update project_briefs
        set status = 'approved', approved_by = %s, approved_at = %s
        where brief_id = %s
    """, (approver, datetime.now(timezone.utc), bid))
    return get_brief(brief_id)


def _brief_row(r: dict) -> dict:
    if not r:
        return {}
    return {
        "id": str(r["brief_id"]),
        "brief_id": r["brief_id"],
        "content": r.get("content") or "",
        "clarity_score": float(r["clarity_score"]) if r.get("clarity_score") is not None else None,
        "status": r.get("status") or "draft",
        "created_at": r["created_at"].isoformat() if r.get("created_at") else "",
        "approved_at": r["approved_at"].isoformat() if r.get("approved_at") else None,
        "meeting_type": r.get("meeting_type") or "discovery_call",
        "client_company": r.get("client_company") or "",
        "client_name": r.get("client_name") or "",
    }


# --------------------------------------------------------------------------
# Reporting — deterministic SQL aggregates, zero LLM
# --------------------------------------------------------------------------
def dashboard_metrics() -> dict:
    r = _one("""
        with proposals_month as (
            select count(*) as c from proposals
            where created_at >= date_trunc('month', current_date)
        ),
        proposals_sent as (
            select count(*) as c from proposals
            where status in ('sent', 'accepted')
        ),
        quotes_total as (
            select coalesce(sum(total_amount), 0) as total,
                   count(*) as c
            from quotes
        ),
        quotes_accepted as (
            select coalesce(sum(total_amount), 0) as total,
                   count(*) as c
            from quotes where status = 'accepted'
        ),
        clients_active as (
            select count(*) as c from clients
            where status in ('active client', 'proposal sent', 'won')
        ),
        briefs_approved as (
            select count(*) as c from project_briefs where status = 'approved'
        )
        select
            (select c from proposals_month)   as proposals_this_month,
            (select c from proposals_sent)     as proposals_sent,
            (select total from quotes_total)   as quoted_total,
            (select c from quotes_total)       as quotes_count,
            (select total from quotes_accepted) as won_total,
            (select c from quotes_accepted)    as won_count,
            (select c from clients_active)     as active_clients,
            (select c from briefs_approved)    as briefs_approved
    """)
    if not r:
        return {}
    return {
        "proposals_this_month": int(r["proposals_this_month"] or 0),
        "proposals_sent":       int(r["proposals_sent"] or 0),
        "quoted_total":         float(r["quoted_total"] or 0),
        "quotes_count":         int(r["quotes_count"] or 0),
        "won_total":            float(r["won_total"] or 0),
        "won_count":            int(r["won_count"] or 0),
        "active_clients":       int(r["active_clients"] or 0),
        "briefs_approved":      int(r["briefs_approved"] or 0),
        "win_rate":             (r["won_count"] / r["quotes_count"] * 100) if r["quotes_count"] else 0,
    }


# --------------------------------------------------------------------------
# Row → Kora shape
# --------------------------------------------------------------------------
def _proposal_row_to_kora(r: dict) -> dict:
    if not r:
        return {}
    deliverables = r.get("deliverables_list")
    if isinstance(deliverables, str):
        try: deliverables = json.loads(deliverables)
        except Exception: deliverables = []
    return {
        "id": str(r["proposal_id"]),
        "number": f"{r['proposal_id']:04d}",
        "title": (r.get("scope_of_work") or "").split("\n")[0][:120] or "Untitled",
        "scope": r.get("scope_of_work") or "",
        "summary": (r.get("scope_of_work") or "")[:200],
        "deliverables": deliverables or [],
        "status": r.get("status") or "draft",
        "version": r.get("version") or 1,
        "created_at": r["created_at"].isoformat() if r.get("created_at") else "",
        "client_name": r.get("client_name") or "",
        "client_company": r.get("client_company") or "",
    }


def _quote_row_to_kora(r: dict) -> dict:
    if not r:
        return {}
    li = r.get("line_items")
    if isinstance(li, str):
        try: li = json.loads(li)
        except Exception: li = []
    quickbooks = None
    if isinstance(li, dict) and "items" in li:
        quickbooks = li.get("quickbooks")
        li = li.get("items") or []
    return {
        "id": str(r["quote_id"]),
        "number": f"{r['quote_id']:04d}",
        "title": (r.get("scope_of_work") or "").split("\n")[0][:120] or f"Quote {r['quote_id']}",
        "currency": r.get("currency") or "KES",
        "tax_rate": float(r.get("tax_rate") or 0),
        "discount_amount": float(r.get("discount_amount") or 0),
        "total": float(r.get("total_amount") or 0),
        "subtotal": float(r.get("total_amount") or 0),
        "status": r.get("status") or "draft",
        "line_items": li or [],
        "quickbooks": quickbooks,
        "created_at": r["created_at"].isoformat() if r.get("created_at") else "",
        "client_name": r.get("client_name") or "",
        "client_company": r.get("client_company") or "",
    }


def _timeline_json(data: dict) -> Any:
    tl = data.get("timeline")
    if isinstance(tl, (list, dict)):
        return tl
    if isinstance(tl, str) and tl.strip():
        return [{"label": tl}]
    return []
