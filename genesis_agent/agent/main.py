"""
Genesis meeting-intelligence agent — Step 1 (Option A) + questions & branded docs.

Endpoints:
  GET  /                      redirect to /docs
  GET  /health                liveness + directory paths
  GET  /activity              recent capture events
  GET  /captures              list of saved captures
  GET  /captures/{name}       one capture (raw JSON on disk)
  GET  /captures/{name}/questions   suggested questions for the team
  POST /webhook/fathom        Fathom / Zapier posts summaries here
  POST /webhook/fathom/script paste a raw script/transcript, no JSON required
  POST /webhook/fathom/native Fathom's own automated webhook (HMAC-verified)
  GET  /brand                 the loaded brand config (sanity check)
  POST /render/proposal.html  render a proposal to HTML from a JSON body
  POST /render/proposal.pdf   same, but return a PDF (if WeasyPrint installed)
  POST /render/quote.html     render a quote to HTML
  POST /render/quote.pdf      same, PDF
  GET  /preview/proposal      one-click demo render of a sample proposal
  GET  /preview/quote         one-click demo render of a sample quote
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import os
from pathlib import Path
from typing import Literal, Optional

from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from fastapi import Body, FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, Response, RedirectResponse
from pydantic import BaseModel, ConfigDict

from agent import brand as brand_mod
from agent import brief as brief_mod, capture, db, flask_bridge, llm_client, questions, quickbooks, renderer, store, watcher
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
import json as _json

_pages = Jinja2Templates(directory='templates')
# Newer Starlette TemplateResponse + Jinja2's LRUCache put an unhashable dict
# into the cache key (pallets/jinja#2180). Disabling the cache sidesteps it.
_pages.env.cache = None

app = FastAPI(title="Genesis meeting-intelligence agent")


@app.on_event("startup")
async def _startup():
    db.init()
    asyncio.create_task(watcher.watch_loop())

@app.on_event("shutdown")
async def _shutdown():
    db.close()


@app.get("/")
def root():
    return RedirectResponse("/docs")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "mode": "option_a_capture_only",
        "inbox": str(watcher.INBOX.resolve()),
        "captures_dir": str(capture.CAPTURES_DIR.resolve()),
        "known_captures": len(capture._seen),
    }


@app.get("/activity")
def activity():
    return {"activity": capture.recent}


@app.get("/captures")
def list_captures():
    files = sorted(capture.CAPTURES_DIR.glob("*.json"),
                   key=lambda p: p.stat().st_mtime, reverse=True)
    return {"captures": [p.name for p in files]}


@app.get("/captures/{name}")
def get_capture(name: str):
    p = capture.CAPTURES_DIR / name
    if not p.exists():
        raise HTTPException(404, "Capture not found.")
    return json.loads(p.read_text(encoding="utf-8"))


@app.get("/captures/{name}/questions")
def capture_questions(name: str):
    p = capture.CAPTURES_DIR / name
    if not p.exists():
        raise HTTPException(404, "Capture not found.")
    data = json.loads(p.read_text(encoding="utf-8"))
    # Coverage is stored at capture time; re-analysing means template edits
    # take effect without re-capturing.
    return questions.analyse(data.get("summary", ""))


# The frontend decides this — no more guessing from speaker-domain heuristics
# or a nested "meeting.meeting_type" field. Discovery calls haven't had scope
# or pricing locked yet, so they just get the summary + deliverables back.
# Internal meetings are where the team locks both, so they go straight to a
# draft proposal + quote via the templates — zero extra LLM tokens either way.
_MEETING_TYPE_ALIASES = {
    "discovery_meeting": "discovery_call",
    "internal": "internal",
}

FathomMeetingType = Literal["discovery_meeting", "internal"]


class FathomWebhookPayload(BaseModel):
    """Fathom's own fields, or a pre-digested call-intelligence payload —
    any shape is accepted (extra="allow"); only meeting_type is required."""
    model_config = ConfigDict(extra="allow")
    meeting_type: FathomMeetingType


def _capture_payload(payload: dict, meeting_type: Optional[str] = None,
                      deliver: str = "local",
                      extra_action_items: Optional[list] = None) -> dict:
    """meeting_type is optional — when the caller doesn't have a human
    around to set it (an automated webhook), it falls through to the same
    auto-classify capture.py already does for a raw transcript
    (participant email-domain heuristic in save_capture ->
    classify_meeting_type), via meeting_type_hint="" below.

    deliver="local" (default, used by /webhook/fathom and
    /webhook/fathom/script): draft proposal/quote via _internal_meeting_
    deliverables(), which writes to genesis_agent's own local store — for
    the script endpoint, Nuxt then does its own separate POST to Flask
    with this data, so nothing here needs to reach Flask directly.

    deliver="flask" (used only by /webhook/fathom/native): there's no Nuxt
    in the loop for an automated webhook, so this calls flask_bridge to
    create the real Proposal/Quote/Summary directly — otherwise an
    automated capture would never show up anywhere in the actual app."""
    resolved_hint = _MEETING_TYPE_ALIASES[meeting_type] if meeting_type else ""
    # Top-level meeting_type is our own routing control field, not meeting
    # content — drop it so it doesn't leak into the flattened summary text.
    payload = {k: v for k, v in payload.items() if k != "meeting_type"}

    parts = capture.extract_from_payload(payload)
    if not parts["summary"]:
        return {"ok": False,
                "reason": "No summary field found in payload.",
                "seen_keys": sorted(list(payload.keys()))[:20]}

    record = capture.save_capture(
        source="webhook",
        summary=parts["summary"],
        title=parts["title"],
        external_id=parts["external_id"],
        raw=parts.get("structured_root") or payload,
        # A structured payload's own meeting.meeting_type (parts[...]) wins
        # as the fallback over blind classification when there's no
        # explicit caller-supplied meeting_type either.
        meeting_type_hint=resolved_hint or parts["meeting_type_hint"],
        extra_action_items=parts.get("action_items", []) + (extra_action_items or []),
        meeting_occurred_at=parts.get("meeting_occurred_at", ""),
    )
    # save_capture() resolves the final "discovery_call" | "internal" value
    # (auto-classifying from participants if both hints above were empty)
    # — read it back rather than trusting whatever we passed in.
    resolved_meeting_type = record["meeting_type"]
    key_points = record.get("key_points", {})

    if deliver == "flask":
        if resolved_meeting_type == "internal":
            proposal_data = _proposal_data_from_key_points(record.get("title", ""), key_points)
            line_items = _quote_line_items_from_key_points(key_points)
            result = flask_bridge.deliver_internal_meeting(key_points, proposal_data, line_items)
        else:
            result = flask_bridge.deliver_discovery_call(key_points)
        return {"meeting_type": resolved_meeting_type, "captured": record, **result}

    if resolved_meeting_type == "internal":
        return _internal_meeting_deliverables(record)

    deliverables = _proposal_data_from_key_points(
        record.get("title", ""), key_points
    )["deliverables"]
    return {"ok": True, "meeting_type": "discovery_call", "captured": record,
            "summary": parts["summary"], "deliverables": deliverables}


def _internal_meeting_deliverables(record: dict) -> dict:
    """Internal meeting -> draft proposal + quote straight from key_points,
    rendered through the same Jinja templates /proposals and /quotes use.
    No LLM call — the structured extraction already happened at capture
    time (and was cached if it went through the script endpoint)."""
    key_points = record.get("key_points", {})
    proposal_data = _proposal_data_from_key_points(record.get("title", ""), key_points)
    proposal_data["meeting_occurred_at"] = record.get("meeting_occurred_at", "")

    try:
        proposal = store.save_proposal(proposal_data)
        quote = store.save_quote({
            "proposal_id": proposal.get("id"),
            "client_company": proposal_data["client_company"],
            "client_name": proposal_data["client_name"],
            "title": proposal_data["title"],
            "line_items": _quote_line_items_from_key_points(key_points),
            "currency": (key_points.get("budget") or {}).get("currency", "KES"),
            "status": "draft",
        })
    except Exception as exc:
        return {"ok": False, "meeting_type": "internal", "captured": record,
                "reason": f"Could not draft proposal/quote: {exc}"}

    return {
        "ok": True,
        "meeting_type": "internal",
        "captured": record,
        "proposal": proposal,
        "quote": quote,
        "proposal_html": renderer.render_proposal_html(proposal),
        "quote_html": renderer.render_quote_html(quote),
        "proposal_url": f"/proposals/{proposal.get('id')}",
        "quote_url": f"/quotes/{quote.get('id')}",
    }


@app.post("/webhook/fathom")
async def fathom_webhook(payload: FathomWebhookPayload):
    """For automations that already send JSON — Fathom's own fields, or a
    pre-digested call-intelligence payload. meeting_type is required:
    "discovery_meeting" gets back the summary + deliverables; "internal"
    (scope/pricing already locked by the team) gets back a draft proposal +
    quote rendered from the templates. Zero LLM tokens either way."""
    return _capture_payload(payload.model_dump(), payload.meeting_type)


@app.post("/webhook/fathom/script")
async def fathom_webhook_script(meeting_type: FathomMeetingType,
                                text: str = Body(..., media_type="text/plain")):
    """For pasting a raw script/transcript straight from Fathom — no JSON
    required. meeting_type is a required query parameter (send it as
    ?meeting_type=discovery_meeting or ?meeting_type=internal).

    We never trust a third party's own AI-generated summary (Fathom's
    included) — only the transcript itself. A JSON body only skips our own
    LLM extraction (zero tokens) when it's already our own structured shape
    (e.g. a Zapier step that ran extraction upstream); any other JSON shape
    — including Fathom's real webhook payload, which carries both a
    transcript field and its own summary/ai_summary fields — has its
    transcript field pulled out and run through our own extraction, same as
    plain pasted text. meeting_type here always wins over whatever the
    extraction infers."""
    text = (text or "").strip()
    if not text:
        return {"ok": False, "reason": "Empty body."}

    try:
        parsed = json.loads(text)
    except Exception:
        parsed = None

    if isinstance(parsed, dict) and capture.is_pre_digested(parsed):
        payload = parsed
    else:
        raw_text = capture.raw_transcript_text(parsed) if isinstance(parsed, dict) else text
        if not raw_text:
            return {"ok": False, "reason": "No transcript text found in the payload."}
        payload = capture.extract_structured_via_llm(raw_text) or {"transcript": raw_text}

    return _capture_payload(payload, meeting_type)


# --------------------------- native Fathom webhook ---------------------------
# Fathom's own webhook (Settings -> API Access -> Add Webhook), as opposed to
# the two endpoints above (a Zapier step, or a human pasting a script) — this
# one fires automatically with nobody around to authenticate the request or
# pick a meeting_type by hand, so both of those get handled here instead.
FATHOM_WEBHOOK_SECRET = os.getenv("FATHOM_WEBHOOK_SECRET", "")


def _verify_fathom_signature(body: bytes, webhook_id: str, webhook_timestamp: str,
                              signature_header: str) -> bool:
    """Svix-style HMAC-SHA256 verification — the scheme behind the
    webhook-id / webhook-timestamp / webhook-signature headers and the
    whsec_... secret format Fathom's webhook docs describe. Fails closed:
    no secret configured, or any header missing, means "reject."

    NOT YET CONFIRMED against a real Fathom-signed request — Fathom's docs
    describe this exact header/secret convention but a live payload to test
    against hasn't been captured yet. Verify this once real traffic flows
    before fully trusting it in production.
    """
    if not FATHOM_WEBHOOK_SECRET or not (webhook_id and webhook_timestamp and signature_header):
        return False
    try:
        secret_bytes = base64.b64decode(FATHOM_WEBHOOK_SECRET.removeprefix("whsec_"))
    except Exception:
        return False

    signed_content = f"{webhook_id}.{webhook_timestamp}.{body.decode('utf-8')}"
    expected = base64.b64encode(
        hmac.new(secret_bytes, signed_content.encode("utf-8"), hashlib.sha256).digest()
    ).decode("utf-8")

    provided = [part.split(",", 1)[1] for part in signature_header.split() if "," in part]
    return any(hmac.compare_digest(expected, sig) for sig in provided)


@app.post("/webhook/fathom/native")
async def fathom_webhook_native(
    request: Request,
    meeting_type: Optional[FathomMeetingType] = None,
    webhook_id: str = Header(default="", alias="webhook-id"),
    webhook_timestamp: str = Header(default="", alias="webhook-timestamp"),
    webhook_signature: str = Header(default="", alias="webhook-signature"),
):
    """Fathom's real, automated webhook. HMAC-verified (see above).
    Payload shape confirmed against a real captured Fathom delivery
    (transcript is a list of {speaker, text, timestamp} turns, not a flat
    string — handled by capture.raw_transcript_text() /
    _flatten_fathom_transcript()).

    meeting_type resolution order: an explicit query param (never sent by
    Fathom itself, but usable for manual testing) -> Fathom's own
    calendar_invitees[].is_external signal
    (capture.classify_from_calendar_invitees) -> _capture_payload's
    text-based auto-classify fallback, for payloads with no calendar
    metadata at all.

    Fathom's own structured action_items (assignee/description/playback
    link) are pulled in directly via capture.fathom_action_items() rather
    than relying only on regex-scanning the transcript text for inline
    markers, which Fathom's native format doesn't use.

    This is the only endpoint that delivers via flask_bridge (deliver=
    "flask") — a discovery call creates a real Summary, an internal
    meeting creates a real Proposal + Quote, both directly in Flask's
    database via its own API, with no human pasting anything and no Nuxt
    step in between. See flask_bridge.py for the client-resolution
    shortcuts (placeholder email/industry when a transcript doesn't state
    them) and the required FLASK_API_URL / GENESIS_SYSTEM_USER_ID env vars.

    Signature verification is implemented against the documented Svix
    scheme and confirmed structurally correct against a real captured
    request (header names, whsec_ format, v1,<base64> signature shape all
    match) — not yet confirmed byte-for-byte against a real secret, since
    that requires the actual whsec_... value from whoever registered the
    webhook.
    """
    body = await request.body()
    if not _verify_fathom_signature(body, webhook_id, webhook_timestamp, webhook_signature):
        raise HTTPException(401, "Invalid or missing webhook signature.")

    try:
        parsed = json.loads(body)
    except Exception:
        raise HTTPException(400, "Invalid JSON body.")
    if not isinstance(parsed, dict):
        raise HTTPException(400, "Invalid JSON body.")

    if capture.is_pre_digested(parsed):
        payload = parsed
    else:
        raw_text = capture.raw_transcript_text(parsed)
        if not raw_text:
            return {"ok": False, "reason": "No transcript text found in the payload."}
        payload = capture.extract_structured_via_llm(raw_text) or {"transcript": raw_text}

    # Fathom's own explicit external/internal signal beats guessing from
    # the transcript when neither a human nor the LLM extraction gave us
    # one — see capture.classify_from_calendar_invitees().
    resolved_meeting_type = meeting_type or capture.classify_from_calendar_invitees(parsed)
    extra_action_items = capture.fathom_action_items(parsed)

    return _capture_payload(payload, resolved_meeting_type, deliver="flask",
                             extra_action_items=extra_action_items)


# --------------------------- branded document rendering ---------------------------
@app.get("/brand")
def brand_view():
    """Return the loaded brand config so you can verify a change took effect."""
    return brand_mod.reload()


@app.post("/render/proposal.html", response_class=HTMLResponse)
async def render_proposal_html(request: Request):
    data = await request.json()
    saved = store.save_proposal(data)
    html = renderer.render_proposal_html(saved)
    return HTMLResponse(html, headers={"X-Doc-Id": saved["id"]})


@app.post("/render/proposal-preview.html", response_class=HTMLResponse)
async def render_proposal_preview_html(request: Request):
    """Same branded template as /render/proposal.html, but stateless — no
    store.save_proposal() call, so it never writes a row anywhere. Used by
    the frontend's "Download PDF" button, which needs fresh branded HTML
    for a proposal that already exists in Flask; going through the save-
    then-render endpoint would create a duplicate/orphan proposal row on
    every single download (see CHANGES.md's "Important discovery")."""
    data = await request.json()
    return HTMLResponse(renderer.render_proposal_html(data))


@app.post("/render/quote.html", response_class=HTMLResponse)
async def render_quote_html(request: Request):
    data = await request.json()
    saved = store.save_quote(data)
    html = renderer.render_quote_html(saved)
    return HTMLResponse(html, headers={"X-Doc-Id": saved["id"]})


@app.post("/render/quote-preview.html", response_class=HTMLResponse)
async def render_quote_preview_html(request: Request):
    """Stateless counterpart to /render/quote.html — see
    render_proposal_preview_html's docstring above."""
    data = await request.json()
    return HTMLResponse(renderer.render_quote_html(data))


@app.post("/render/proposal.pdf")
async def render_proposal_pdf(request: Request):
    data = await request.json()
    html = renderer.render_proposal_html(data)
    pdf = renderer.render_pdf(html)
    if pdf is None:
        raise HTTPException(501, "WeasyPrint isn't installed. Use the .html endpoint or install weasyprint.")
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": 'inline; filename="proposal.pdf"'})


@app.post("/render/quote.pdf")
async def render_quote_pdf(request: Request):
    data = await request.json()
    html = renderer.render_quote_html(data)
    pdf = renderer.render_pdf(html)
    if pdf is None:
        raise HTTPException(501, "WeasyPrint isn't installed. Use the .html endpoint or install weasyprint.")
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": 'inline; filename="quote.pdf"'})


# --------------------------- one-click previews ---------------------------
_SAMPLE_PROPOSAL = {
    "number": "20260720-001",
    "title": "Lumen Coffee — rebrand & holiday launch",
    "status": "draft",
    "client_name": "Maya Okoro",
    "client_company": "Lumen Coffee Roasters",
    "summary": ("Specialty roaster moving from wholesale to direct-to-consumer, "
                "needs a full rebrand plus a launch campaign live before the holidays."),
    "objectives": [
        "Reposition Lumen as a consumer coffee brand",
        "Launch a holiday campaign to drive first DTC sales",
        "Establish a consistent visual identity across packaging and web",
    ],
    "approach": ("A focused engagement moving quickly from strategy to production, "
                 "with tight review loops so the founder stays in control at every step. "
                 "Aisha leads brand and packaging; Sam leads launch content."),
    "scope_items": [
        "Brand identity + guidelines",
        "Packaging for 3 SKUs (light, medium, decaf)",
        "6-week social launch campaign",
        "Shopify storefront design",
    ],
    "deliverables": [
        "Logo suite + brand guidelines PDF",
        "Print-ready packaging artwork for 3 SKUs",
        "Editable social campaign kit",
        "Shopify storefront (design + build handoff)",
    ],
    "timeline": "Everything live by mid-November, ~10 weeks from kickoff.",
}
_SAMPLE_QUOTE = {
    "number": "20260720-001",
    "title": "Lumen Coffee — rebrand & holiday launch",
    "status": "draft",
    "client_name": "Maya Okoro",
    "client_company": "Lumen Coffee Roasters",
    "currency": "USD",
    "line_items": [
        {"item": "Brand identity + guidelines", "description": "Logo suite, colour, type, usage rules", "qty": 1, "unit_price": 8000},
        {"item": "Packaging design",           "description": "Print-ready artwork for 3 SKUs",         "qty": 3, "unit_price": 2000},
        {"item": "Social launch campaign",     "description": "6 weeks, editable kit",                  "qty": 1, "unit_price": 4000},
        {"item": "Shopify storefront design",  "description": "Design + build handoff",                 "qty": 1, "unit_price": 3000},
    ],
    "tax_rate": 0,
}


@app.get("/preview/proposal", response_class=HTMLResponse)
def preview_proposal():
    return HTMLResponse(renderer.render_proposal_html(_SAMPLE_PROPOSAL))


@app.get("/preview/quote", response_class=HTMLResponse)
def preview_quote():
    return HTMLResponse(renderer.render_quote_html(_SAMPLE_QUOTE))



# --------------------------- pages (proposals / quotes) ---------------------------
@app.get("/proposals", response_class=HTMLResponse)
def page_proposals(request: Request):
    ctx = {"request": request, "brand": brand_mod.load(),
           "proposals": store.list_proposals()}
    return _pages.TemplateResponse(request, "pages/proposals_list.html", ctx)


@app.get("/quotes", response_class=HTMLResponse)
def page_quotes(request: Request):
    ctx = {"request": request, "brand": brand_mod.load(),
           "quotes": store.list_quotes(),
           "qb_mode": quickbooks.mode(),
           "qb_configured": quickbooks.is_configured()}
    return _pages.TemplateResponse(request, "pages/quotes_list.html", ctx)


@app.get("/proposals/{doc_id}", response_class=HTMLResponse)
def open_proposal(doc_id: str):
    doc = store.get_proposal(doc_id)
    if not doc:
        raise HTTPException(404, "Proposal not found.")
    return HTMLResponse(renderer.render_proposal_html(doc))


@app.get("/quotes/{doc_id}", response_class=HTMLResponse)
def open_quote(doc_id: str):
    doc = store.get_quote(doc_id)
    if not doc:
        raise HTTPException(404, "Quote not found.")
    return HTMLResponse(renderer.render_quote_html(doc))


# --------------------------- QuickBooks ---------------------------
@app.post("/quotes/{doc_id}/send-to-quickbooks")
def send_quote_to_quickbooks(doc_id: str, force: bool = False):
    """Sends the quote to QuickBooks. Approval-gated: the linked proposal
    must be approved by a producer first (unless `force=true`).
    Simulated by default; real sandbox writes when QUICKBOOKS_MODE=sandbox."""
    doc = store.get_quote(doc_id)
    if not doc:
        raise HTTPException(404, "Quote not found.")
    # Approval gate — enforced when the DB is available.
    if db.is_available() and not force:
        pid = doc.get("proposal_id")
        if pid and not db.proposal_is_approved(int(pid)):
            raise HTTPException(
                412,
                "Quote's proposal has not been approved by a producer yet. "
                "Approve at /proposals/{proposal_id}/approve or retry with ?force=true."
            )
    result = quickbooks.send_estimate(doc)
    store.update_quote(doc_id, {"quickbooks": result,
                                 "status": "sent" if result.get("ok") else doc.get("status", "draft")})
    # After the button press, land the user on the QuickBooks-styled preview.
    return RedirectResponse(f"/quickbooks/preview/{doc_id}", status_code=303)


@app.get("/quickbooks/preview/{doc_id}", response_class=HTMLResponse)
def quickbooks_preview(request: Request, doc_id: str):
    doc = store.get_quote(doc_id)
    if not doc:
        raise HTTPException(404, "Quote not found.")
    result = doc.get("quickbooks") or quickbooks.send_estimate(doc)
    ctx = {"request": request, "brand": brand_mod.load(),
           "quote": doc, "result": result,
           "payload_json": _json.dumps(result.get("payload", {}), indent=2)}
    return _pages.TemplateResponse(request, "pages/quickbooks_preview.html", ctx)


@app.get("/quickbooks/status")
def quickbooks_status():
    """Quick health check for the QuickBooks connection."""
    return {"mode": quickbooks.mode(), "configured": quickbooks.is_configured()}



# --------------------------- DB + cost meter ---------------------------
@app.get("/db/status")
def db_status():
    """Whether Kora is reading/writing to Postgres (or why not)."""
    return db.status()


@app.get("/tokens")
def token_report():
    """Live token cost meter. Cache hits are free; totals include estimated USD."""
    return llm_client.cost_report()


# --------------------------- briefs (new artifact) ---------------------------
@app.post("/briefs/from-capture/{name}")
def brief_from_capture(name: str):
    """Generate a project brief from a stored capture. Haiku-tier LLM call
    with response caching — replays are free."""
    cap_file = capture.CAPTURES_DIR / name
    if not cap_file.exists():
        raise HTTPException(404, "Capture not found.")
    import json as _j
    data = _j.loads(cap_file.read_text(encoding="utf-8"))
    summary = data.get("summary", "")

    # Extract client from the capture's title if available.
    title = data.get("title") or "New client"
    meeting_type = data.get("meeting_type", "discovery_call")
    generated = brief_mod.generate_brief(
        summary, client_company=title,
        meeting_type=meeting_type, action_items=data.get("action_items", []),
    )
    generated["meeting_type"] = meeting_type

    if db.is_available():
        try:
            saved = db.save_brief(
                client_company=title,
                client_name="",
                content=generated["content"],
                clarity_score=generated["clarity_score"],
                meeting_type=meeting_type,
            )
            return {"ok": True, "storage": "db", "brief": saved, "mode": generated["mode"],
                    "meeting_type": meeting_type}
        except Exception as exc:
            return {"ok": True, "storage": "memory", "brief": generated, "warning": str(exc)}
    return {"ok": True, "storage": "memory", "brief": generated}


@app.get("/briefs")
def list_briefs():
    if not db.is_available():
        return {"briefs": [], "warning": "DB unavailable."}
    return {"briefs": db.list_briefs()}


@app.get("/briefs/{brief_id}")
def get_brief(brief_id: str):
    if not db.is_available():
        raise HTTPException(503, "DB unavailable.")
    b = db.get_brief(brief_id)
    if not b:
        raise HTTPException(404, "Brief not found.")
    return b


@app.post("/briefs/{brief_id}/approve")
def approve_brief(brief_id: str):
    if not db.is_available():
        raise HTTPException(503, "DB unavailable.")
    b = db.approve_brief(brief_id)
    if not b:
        raise HTTPException(404, "Brief not found.")
    return {"ok": True, "brief": b}


@app.get("/briefs/{brief_id}/html", response_class=HTMLResponse)
def brief_html(brief_id: str):
    """Printable version of a stored brief — the discovery call's brief or
    the internal meeting's recap — so it can be pulled up (or printed to
    PDF from the browser) ahead of the next meeting."""
    if not db.is_available():
        raise HTTPException(503, "DB unavailable.")
    b = db.get_brief(brief_id)
    if not b:
        raise HTTPException(404, "Brief not found.")
    b["number"] = f"{b['brief_id']:04d}"
    return HTMLResponse(renderer.render_brief_html(b))


@app.get("/briefs/{brief_id}/pdf")
def brief_pdf(brief_id: str):
    if not db.is_available():
        raise HTTPException(503, "DB unavailable.")
    b = db.get_brief(brief_id)
    if not b:
        raise HTTPException(404, "Brief not found.")
    b["number"] = f"{b['brief_id']:04d}"
    html = renderer.render_brief_html(b)
    pdf = renderer.render_pdf(html)
    if pdf is None:
        raise HTTPException(501, "WeasyPrint isn't installed. Use /briefs/{id}/html instead.")
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": 'inline; filename="brief.pdf"'})


def _safe_qty(v) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return 1


def _proposal_data_from_key_points(title: str, key_points: dict) -> dict:
    """Map a capture's key_points onto the shape db.save_proposal expects.
    Structured payloads have a real 'deliverables' section; a plain
    transcript capture only has action_items, so that's the fallback."""
    client = key_points.get("client") or {}
    project = key_points.get("project") or {}
    deliverables = []
    for d in key_points.get("deliverables") or []:
        if isinstance(d, dict):
            bits = [d.get("name", ""), d.get("duration", ""),
                    f"x{d['quantity']}" if d.get("quantity") else ""]
            deliverables.append(" — ".join(b for b in bits if b))
        else:
            deliverables.append(str(d))
    if not deliverables:
        deliverables = [a["text"] if isinstance(a, dict) else str(a)
                         for a in key_points.get("action_items", [])]

    timeline = key_points.get("timeline")
    if isinstance(timeline, dict):
        timeline = "; ".join(f"{k.replace('_', ' ')}: {v}" for k, v in timeline.items())
    elif isinstance(timeline, list):
        # The extraction prompt asks for a flat {"<label>":"<value>"} dict,
        # but the LLM doesn't always follow that exactly — sometimes it
        # wraps things in a list instead (e.g. [{"label": "..."}]). Flatten
        # defensively rather than let a raw JSON blob reach the UI.
        parts = []
        for item in timeline:
            if isinstance(item, dict):
                parts.append("; ".join(f"{k.replace('_', ' ')}: {v}" for k, v in item.items()))
            elif item:
                parts.append(str(item))
        timeline = "; ".join(parts)

    requirements = [str(r) for r in (key_points.get("requirements") or []) if r]

    return {
        "client_company": client.get("company") or title,
        "client_name": client.get("primary_contact", ""),
        "title": project.get("name") or title,
        "scope": project.get("objective") or "",
        "deliverables": deliverables,
        "requirements": requirements,
        "timeline": timeline or "",
        "status": "draft",
    }


def _quote_line_items_from_key_points(key_points: dict) -> list:
    items = []
    for d in key_points.get("deliverables") or []:
        if isinstance(d, dict):
            items.append({"item": d.get("name", "Deliverable"),
                          "qty": _safe_qty(d.get("quantity", 1)), "unit_price": 0})
        else:
            items.append({"item": str(d), "qty": 1, "unit_price": 0})
    if not items:
        items = [{"item": a["text"] if isinstance(a, dict) else str(a), "qty": 1, "unit_price": 0}
                 for a in key_points.get("action_items", [])]
    return items


@app.post("/proposals/from-capture/{name}")
def proposal_from_capture(name: str):
    """Turn a capture's key_points — typically the internal meeting where
    the team locks scope and pricing — into a draft proposal plus a
    companion draft quote (line items priced at 0). A manager fills in
    pricing via PUT /quotes/{id} before sending it through /approve."""
    if not db.is_available():
        raise HTTPException(503, "DB unavailable.")
    cap_file = capture.CAPTURES_DIR / name
    if not cap_file.exists():
        raise HTTPException(404, "Capture not found.")
    import json as _j
    data = _j.loads(cap_file.read_text(encoding="utf-8"))
    key_points = data.get("key_points") or {}
    title = data.get("title") or "New client"

    try:
        proposal = db.save_proposal(_proposal_data_from_key_points(title, key_points))
    except Exception as exc:
        raise HTTPException(422, f"Could not draft proposal: {exc}")

    quote = db.save_quote({
        "proposal_id": int(proposal["id"]),
        "line_items": _quote_line_items_from_key_points(key_points),
        "currency": (key_points.get("budget") or {}).get("currency", "KES"),
        "status": "draft",
    })
    return {"ok": True, "proposal": proposal, "quote": quote}


# --------------------------- approval gate ---------------------------
@app.post("/proposals/{proposal_id}/approve")
def approve_proposal(proposal_id: str):
    """Producer approves the proposal. Required before Send-to-QuickBooks."""
    if not db.is_available():
        raise HTTPException(503, "DB unavailable (approval gate needs Postgres).")
    p = db.get_proposal(proposal_id)
    if not p:
        raise HTTPException(404, "Proposal not found.")
    db.log_activity(int(proposal_id), "approved", notes="Producer approved")
    return {"ok": True, "proposal_id": proposal_id,
            "message": "Approved. Send-to-QuickBooks is now unlocked."}


@app.put("/proposals/{proposal_id}")
def edit_proposal(proposal_id: str, patch: dict = Body(...)):
    """Manager edits to a draft — scope / deliverables / timeline — while
    it waits for approval. Blocked once approved so the audit trail can't
    be quietly rewritten after a producer has signed off."""
    if not db.is_available():
        raise HTTPException(503, "DB unavailable.")
    p = db.get_proposal(proposal_id)
    if not p:
        raise HTTPException(404, "Proposal not found.")
    if "status" not in patch and db.proposal_is_approved(int(proposal_id)):
        raise HTTPException(409, "Proposal already approved — edits no longer apply retroactively.")
    return {"ok": True, "proposal": db.update_proposal(proposal_id, patch)}


@app.put("/quotes/{quote_id}")
def edit_quote(quote_id: str, patch: dict = Body(...)):
    """Manager edits to a draft quote — line items, tax, discount, currency,
    validity — while its linked proposal waits for approval."""
    if not db.is_available():
        raise HTTPException(503, "DB unavailable.")
    q = db.get_quote(quote_id)
    if not q:
        raise HTTPException(404, "Quote not found.")
    return {"ok": True, "quote": db.update_quote(quote_id, patch)}


@app.get("/proposals/{proposal_id}/history")
def proposal_history(proposal_id: str):
    """Audit trail of a proposal — generated, edited, approved, sent, etc."""
    if not db.is_available():
        return {"history": [], "warning": "DB unavailable."}
    pid = int(proposal_id)
    return {"proposal_id": proposal_id, "approved": db.proposal_is_approved(pid),
            "history": db.proposal_history(pid)}


# --------------------------- dashboard (reporting) ---------------------------
@app.get("/dashboard")
def dashboard_data():
    """Aggregate metrics — pure SQL, zero LLM."""
    if db.is_available():
        return {"storage": "db", "metrics": db.dashboard_metrics()}
    # Fallback: count files on disk.
    props = store.list_proposals()
    quotes = store.list_quotes()
    total = sum((q.get("total") or 0) for q in quotes)
    return {"storage": "files", "metrics": {
        "proposals_this_month": len(props),
        "proposals_sent": sum(1 for p in props if p.get("status") in ("sent", "accepted")),
        "quoted_total": total,
        "quotes_count": len(quotes),
        "won_total": sum((q.get("total") or 0) for q in quotes if q.get("status") == "accepted"),
        "won_count": sum(1 for q in quotes if q.get("status") == "accepted"),
        "active_clients": 0,
        "briefs_approved": 0,
        "win_rate": 0,
    }}


@app.get("/dashboard/view", response_class=HTMLResponse)
def dashboard_view(request: Request):
    data = dashboard_data()
    ctx = {"request": request, "brand": brand_mod.load(),
           "metrics": data["metrics"], "storage": data["storage"],
           "cost": llm_client.cost_report(),
           "db_status": db.status()}
    return _pages.TemplateResponse(request, "pages/dashboard.html", ctx)
