"""
Bridge from genesis_agent's automated Fathom webhook (/webhook/fathom/native)
to the real Flask backend.

Without this, the native webhook only wrote into genesis_agent's own local
store (db.py's raw SQL insert — the duplicate-write issue in CHANGES.md),
which is never referenced again by the actual app. This module is what
turns "Fathom sent us a transcript" into a real, visible Proposal/Quote/
Summary in the same database Flask/Nuxt already serve — the same shape
Nuxt's handleInternalMeeting()/handleDiscoveryMeeting() produce today, just
triggered automatically instead of by a human pasting a transcript.

Used ONLY by /webhook/fathom/native. The existing /webhook/fathom and
/webhook/fathom/script paths are untouched — they still hand their result
back to Nuxt, which does its own POST to Flask. Fixing that path's
duplicate-write too is separate, larger work (would need a Nuxt change as
well) and wasn't part of this pass.
"""
from __future__ import annotations

import os
import re
from typing import Optional

FLASK_API_URL = os.getenv("FLASK_API_URL", "")
# Attributed as created_by_user_id / user_id on everything this bridge
# creates. There's no human logged in during an automated webhook, so this
# has to be an existing real id from Flask's `users` table — set it to
# whichever account should "own" AI-captured records.
GENESIS_SYSTEM_USER_ID = os.getenv("GENESIS_SYSTEM_USER_ID", "")


def _configured() -> bool:
    return bool(FLASK_API_URL and GENESIS_SYSTEM_USER_ID)


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (s or "").lower()).strip("_") or "unknown"


def _post(path: str, body: dict):
    import requests  # imported lazily — only this module needs it
    resp = requests.post(f"{FLASK_API_URL}{path}", json=body, timeout=10)
    resp.raise_for_status()
    return resp.json()


def find_or_create_client(company: str, name: str, email: str, industry: str) -> Optional[int]:
    """Flask has no by-email lookup endpoint, so this tries to create
    first (the common case: a brand-new client from a first-ever meeting)
    and falls back to a company-name search on the 409 "already exists"
    response create_client raises for a duplicate email.

    When a transcript doesn't name an email (the common case — people
    rarely state one in conversation), synthesizes one the same way
    genesis_agent's own db.py already does for its local writes:
    "<slugified-company>@unknown.local". This is a real placeholder, not a
    contact address — same shortcut, just now visible in Flask's real
    client records instead of an orphaned local one."""
    import requests

    company = company or name or "Unknown company"
    email = email or f"{_slug(company)}@unknown.local"
    payload = {
        "user_id": int(GENESIS_SYSTEM_USER_ID),
        "name": name or company,
        "company": company,
        "industry": industry or "Unspecified",
        "email": email,
    }

    try:
        resp = requests.post(f"{FLASK_API_URL}/clients", json=payload, timeout=10)
        if resp.status_code == 201:
            return resp.json()["data"]["client_id"]
        if resp.status_code == 409:
            # Approximate — company-name search, not a real email index.
            # Takes the first match; good enough for a single-agency scale,
            # not a substitute for a real lookup endpoint.
            found = requests.get(
                f"{FLASK_API_URL}/clients", params={"search": company, "limit": 20}, timeout=10
            )
            found.raise_for_status()
            matches = found.json().get("data", [])
            for client in matches:
                if client.get("email", "").lower() == email.lower():
                    return client["client_id"]
            if matches:
                return matches[0]["client_id"]
        return None
    except Exception as exc:
        print(f"[flask_bridge] find_or_create_client failed: {exc}")
        return None


def deliver_discovery_call(key_points: dict) -> dict:
    """POST /summaries — mirrors Nuxt's handleDiscoveryMeeting()."""
    if not _configured():
        return {"ok": False,
                "reason": "FLASK_API_URL / GENESIS_SYSTEM_USER_ID not configured — "
                          "see genesis_agent/.env.example."}

    client_info = key_points.get("client") or {}
    client_id = find_or_create_client(
        company=client_info.get("company", ""),
        name=client_info.get("primary_contact", ""),
        email=client_info.get("email", ""),
        industry=client_info.get("industry", ""),
    )
    if not client_id:
        return {"ok": False, "reason": "Could not resolve a client for this meeting."}

    try:
        summary = _post("/summaries", {
            "user_id": int(GENESIS_SYSTEM_USER_ID),
            "client_id": client_id,
            "first_meeting_deliverables": key_points,
        })
        return {"ok": True, "summary": summary}
    except Exception as exc:
        return {"ok": False, "reason": f"Could not save summary: {exc}"}


def deliver_internal_meeting(key_points: dict, proposal_data: dict, line_items: list) -> dict:
    """POST /proposals then /quotes — mirrors Nuxt's handleInternalMeeting().
    An internal meeting almost always follows an earlier discovery call, so
    the client should usually already exist; find_or_create_client()'s
    create-first approach still handles it correctly either way (409 ->
    finds the existing one)."""
    if not _configured():
        return {"ok": False,
                "reason": "FLASK_API_URL / GENESIS_SYSTEM_USER_ID not configured — "
                          "see genesis_agent/.env.example."}

    client_info = key_points.get("client") or {}
    client_id = find_or_create_client(
        company=client_info.get("company", "") or proposal_data.get("client_company", ""),
        name=client_info.get("primary_contact", "") or proposal_data.get("client_name", ""),
        email=client_info.get("email", ""),
        industry=client_info.get("industry", ""),
    )
    if not client_id:
        return {"ok": False, "reason": "Could not resolve a client for this meeting."}

    try:
        proposal_resp = _post("/proposals", {
            "client_id": client_id,
            "user_id": int(GENESIS_SYSTEM_USER_ID),
            "scope_of_work": proposal_data.get("scope", ""),
            "deliverables_list": proposal_data.get("deliverables", []),
            "requirements_checklist": proposal_data.get("requirements", []),
            "timeline_milestones": proposal_data.get("timeline", ""),
            "meeting_occurred_at": proposal_data.get("meeting_occurred_at", ""),
            "generated_by": "AI-drafted",
            "status": "draft",
        })
        proposal = proposal_resp["data"]

        total = round(sum(i["qty"] * i["unit_price"] for i in line_items), 2)
        quote_resp = _post("/quotes", {
            "proposal_id": proposal["proposal_id"],
            "user_id": int(GENESIS_SYSTEM_USER_ID),
            "currency": (key_points.get("budget") or {}).get("currency", "KES"),
            "total_amount": total,
            "line_items": line_items,
        })
        return {"ok": True, "proposal": proposal, "quote": quote_resp["data"]}
    except Exception as exc:
        return {"ok": False, "reason": f"Could not save proposal/quote: {exc}"}
