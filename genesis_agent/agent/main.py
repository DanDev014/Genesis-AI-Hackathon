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
import json
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, Response, RedirectResponse
from pydantic import BaseModel, ConfigDict

from agent import brand as brand_mod
from agent import brief as brief_mod, capture, db, llm_client, questions, quickbooks, renderer, store, watcher
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


def _capture_payload(payload: dict, meeting_type: str) -> dict:
    meeting_type = _MEETING_TYPE_ALIASES[meeting_type]
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
        meeting_type_hint=meeting_type,
        extra_action_items=parts.get("action_items", []),
    )

    if meeting_type == "internal":
        return _internal_meeting_deliverables(record)

    deliverables = _proposal_data_from_key_points(
        record.get("title", ""), record.get("key_points", {})
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
    ?meeting_type=discovery_meeting or ?meeting_type=internal). If the body
    happens to already be JSON, that's used directly (zero tokens, same as
    /webhook/fathom). Otherwise one cached, fast-tier LLM call turns it into
    the same structured shape before it enters the normal capture pipeline —
    meeting_type here always wins over whatever the extraction infers."""
    text = (text or "").strip()
    if not text:
        return {"ok": False, "reason": "Empty body."}

    try:
        parsed = json.loads(text)
        payload = parsed if isinstance(parsed, dict) else {"transcript": text}
    except Exception:
        payload = capture.extract_structured_via_llm(text) or {"transcript": text}

    return _capture_payload(payload, meeting_type)


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


@app.post("/render/quote.html", response_class=HTMLResponse)
async def render_quote_html(request: Request):
    data = await request.json()
    saved = store.save_quote(data)
    html = renderer.render_quote_html(saved)
    return HTMLResponse(html, headers={"X-Doc-Id": saved["id"]})


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

    return {
        "client_company": client.get("company") or title,
        "client_name": client.get("primary_contact", ""),
        "title": project.get("name") or title,
        "scope": project.get("objective") or "",
        "deliverables": deliverables,
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
