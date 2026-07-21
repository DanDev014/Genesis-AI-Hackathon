# Genesis meeting-intelligence agent — Step 1 (Option A)

Fathom records the Zoom call and its own AI produces the summary. Our agent:

1. **Notices** the summary the moment it arrives (folder drop or webhook).
2. **Captures** it as a JSON record with a fingerprint (idempotent).
3. **Suggests questions** the team hasn't yet answered, from a template.
4. **Renders** branded proposals and quotations with a shared letterhead.

Step 1 makes **zero LLM calls** — everything below is deterministic and cheap.
Steps 2+ will add Claude for structured extraction, brief drafting, etc.

```
Fathom summary  →  captured  →  suggested questions  →  branded proposal + quote
```

---

## Setup

```bash
cd genesis-agent
python -m venv .venv
source .venv/Scripts/activate     # Git Bash on Windows
# or: .venv\Scripts\activate      # PowerShell / cmd
pip install -r requirements.txt
```

No API key needed for Step 1.

## Run

```bash
uvicorn agent.main:app --reload --port 8000
```

Open **http://localhost:8000/docs** for the clickable API. The two most fun
endpoints for a first look:

- **http://localhost:8000/preview/proposal** — a fully-rendered sample proposal
- **http://localhost:8000/preview/quote** — a fully-rendered sample quotation

## Demo the full loop

```bash
# 1. Drop a Fathom summary into the inbox
cp sample_fathom_summary.md inbox/

# 2. Watch the uvicorn window: [capture] captured: 20260720-xxxx__...json

# 3. See what the agent picked up
curl http://localhost:8000/activity
curl http://localhost:8000/captures

# 4. See which template questions the team already covered — and which they didn't
curl "http://localhost:8000/captures/<the-filename>.json/questions"
```

The `.../questions` response is a coverage report:
```json
{
  "coverage_percent": 67,
  "covered": [{"topic": "Budget range", "matched": "budget"}, ...],
  "missing": [
    {"priority": "high", "topic": "Success metrics",
     "question": "How will you know this project has been successful three months after launch?",
     "why": "Without a metric, 'good' becomes subjective in reviews."},
    ...
  ]
}
```

## Suggested-questions template

Lives at **`templates/questions/default.yaml`**. Each item has `signals`
(keywords that count as "already covered") and a `question` to ask if none
of the signals appear in the summary. Priority ordering is built in.

Swap this file for Genesis's real template whenever it's ready — no code
change, as long as the shape stays the same.

## Branded proposal + quote

Two Jinja2 templates share a single `_base.html` with the letterhead, palette,
footer, signature block, and typography. All values come from a single config:

- **`brand/brand.yaml`** — company name, tagline, palette, contact, signature.
- **`brand/logo.svg`** — logo (base64-inlined so PDFs are self-contained).

Change one file, both documents update.

### Render endpoints

```bash
# HTML (works everywhere)
curl -X POST http://localhost:8000/render/proposal.html \
  -H "Content-Type: application/json" \
  -d @proposal_data.json

# PDF (needs weasyprint; optional)
curl -X POST http://localhost:8000/render/quote.pdf \
  -H "Content-Type: application/json" \
  -d @quote_data.json  --output quote.pdf
```

Minimal proposal body:
```json
{
  "number": "P-001",
  "title": "Lumen Coffee — rebrand",
  "client_company": "Lumen Coffee Roasters",
  "client_name": "Maya Okoro",
  "summary": "Two-sentence pitch.",
  "objectives": ["Reposition as consumer brand", "Launch by mid-November"],
  "deliverables": ["Logo suite", "Packaging x3", "Storefront"],
  "timeline": "10 weeks"
}
```

Minimal quote body:
```json
{
  "number": "Q-001",
  "title": "Lumen Coffee — rebrand",
  "client_company": "Lumen Coffee Roasters",
  "currency": "USD",
  "line_items": [
    {"item": "Brand identity", "description": "Logo, colour, type", "qty": 1, "unit_price": 8000},
    {"item": "Packaging",      "description": "3 SKUs",             "qty": 3, "unit_price": 2000}
  ],
  "tax_rate": 0
}
```

Totals compute themselves; `valid_until` is set from `quote_valid_days` in
`brand.yaml`.

### About PDF rendering

PDF rendering uses **WeasyPrint**, which needs Pango/Cairo on Windows and can
be fiddly to install. If `pip install weasyprint` doesn't cooperate:

- The HTML endpoints look identical to the PDF and any browser can save them
  as a PDF via **Ctrl-P → Save as PDF**.
- Or install WeasyPrint via conda: `conda install -c conda-forge weasyprint`.

## Payload tolerance (webhook)

Fathom and Zapier put the summary under different field names. The webhook
checks these keys, top level and nested under `data` / `meeting` / `event`:
`summary`, `meeting_summary`, `ai_summary`, `ai_notes`, `notes`,
`meeting_notes`, `action_items`, `transcript`. First non-empty wins. If none
match, you get `ok: false` with the keys we saw, so you can pin the right
field on your plan in ten seconds.

## Paste a raw script (webhook)

`POST /webhook/fathom/script` takes a plain-text body — paste a raw Fathom
transcript straight in, no JSON required.

- If the pasted text happens to already be JSON (Fathom's own fields, or a
  pre-digested call-intelligence payload), it's used as-is — same zero-token
  path as `/webhook/fathom`.
- Otherwise, one cached, fast-tier Gemini call (`gemini-flash-lite-latest`)
  turns the transcript into the same structured shape — project, client,
  deliverables, timeline, budget, risks, next_steps — before it enters the
  normal capture pipeline. Works the same for a discovery call or an
  internal meeting; `meeting_type` comes out of the extraction itself,
  cross-checked against the "external domain in parentheses" heuristic used
  elsewhere. No API key configured, or the call fails? Falls back to the
  zero-token regex/keyword extraction — never breaks the capture.
- Identical transcripts (Fathom retries, or re-testing) hit the LLM cache —
  zero additional tokens.

## What's next

- ~~**Step 2** — Claude extraction: turn each capture into a structured
  client record (company, budget, deliverables, pain points).~~ Done, via
  `/webhook/fathom/script` above (Gemini rather than Claude).
- **Step 3** — internal brief written from the structured record.
- **Step 4** — proposal + quote *content* auto-generated from the brief, then
  rendered into the templates you just saw.
- **Step 5** — persist to Neon, add the UI, wire the email send.


---

## Pages (new)

Two browsable pages, both served directly by FastAPI (no build step, no npm):

- **http://127.0.0.1:8000/proposals** — every proposal ever rendered, newest first.
- **http://127.0.0.1:8000/quotes**    — every quote, with totals and a **Send to QuickBooks** button.

Every time you POST to `/render/proposal.html` or `/render/quote.html`, the
document is now also saved to `proposals/` or `quotes/` on disk. From there
each has its own stable URL:

- `/proposals/{id}` — reopen a stored proposal
- `/quotes/{id}`    — reopen a stored quote

## QuickBooks (new)

The Quotes page has a **Send to QuickBooks** button per row. It maps the
quote to Intuit's Estimate object and either simulates the send or does a
real sandbox write.

**Mode is controlled by one env var:**

```bash
# Simulated (default). Zero external dependency, safe on stage.
# QUICKBOOKS_MODE unset  →  simulated

# Live sandbox writes to Intuit's QuickBooks Online sandbox company.
QUICKBOOKS_MODE=sandbox
QUICKBOOKS_CLIENT_ID=...
QUICKBOOKS_CLIENT_SECRET=...
QUICKBOOKS_REFRESH_TOKEN=...
QUICKBOOKS_REALM_ID=...
```

Get the four values from https://developer.intuit.com → create an app →
sandbox tab. Both modes produce the identical Estimate payload; only the
send differs.

**What happens when you click Send to QuickBooks:**

1. The quote is translated to QuickBooks' Estimate JSON shape (CustomerRef,
   Line items with ItemRef, ExpirationDate, TotalAmt, CurrencyRef).
2. In simulated mode: a fake QuickBooks response is returned with a
   `SIM-<num>` Estimate id; the quote is marked sent; the page shows a
   QuickBooks-styled preview at `/quickbooks/preview/{id}`.
3. In sandbox mode: the payload actually POSTs to `sandbox-quickbooks.api.intuit.com`,
   the real Estimate id comes back, and Genesis can see it in their QuickBooks
   sandbox UI.

Check current mode any time at **`/quickbooks/status`**.

## Files added

```
agent/store.py                              proposals / quotes storage
agent/quickbooks.py                         payload builder + simulated/sandbox dispatch
templates/pages/proposals_list.html         /proposals page
templates/pages/quotes_list.html            /quotes page
templates/pages/quickbooks_preview.html     QB-styled preview after send
proposals/                                  saved proposal JSONs
quotes/                                     saved quote JSONs
```


---

## Neon Postgres (new)

Paste your Neon connection string into `.env` and everything persists there —
proposals, quotes, briefs, and the audit trail. No connection? Kora falls back
to file storage automatically. Check state at `/db/status`.

```
DATABASE_URL=postgresql://user:password@ep-xxxx-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require
```

## Project briefs (new)

The "single source of truth" between capture and proposal. Endpoint:

```
POST /briefs/from-capture/{capture-filename}
```

Turns the stored Fathom summary into a short markdown brief. Uses Claude
(Haiku tier, cached, metered). Falls back to a deterministic template if
`ANTHROPIC_API_KEY` isn't set. Includes a `clarity_score` derived from the
coverage engine — no separate LLM call needed.

Then:
- `GET  /briefs` — list all briefs
- `GET  /briefs/{id}` — one brief
- `POST /briefs/{id}/approve` — mark it approved (producer action)

## Approval gate (new)

Quotes cannot be pushed to QuickBooks until the linked proposal has been
approved. If you try, you get a `412 Precondition Failed` with a clear
message. Bypass in dev with `?force=true`.

- `POST /proposals/{id}/approve` — producer approves the proposal
- `GET  /proposals/{id}/history` — audit trail from `proposal_activity_log`

## Reporting dashboard (new)

Deterministic SQL aggregates — zero LLM tokens.

- `GET /dashboard` — JSON metrics
- `GET /dashboard/view` — the rendered page

Shows: proposals this month, proposals sent, total KES quoted, KES won,
win rate, active clients, briefs approved. Also displays the live token
efficiency panel.

## Token efficiency (new)

Every Claude call in Kora goes through `agent/llm_client.py`. That gives us:

1. **Model tiering.** Haiku by default, Sonnet only when reasoning demands it.
2. **Response caching.** SHA-256 of `(system + user + tier)`. Cache hits cost 0 tokens.
3. **Live meter.** `GET /tokens` shows total calls, cache hit rate, per-tier tokens, estimated USD.
4. **Idempotent webhooks.** Fathom retries hit the fingerprint dedup before any LLM call.
5. **Deterministic-first.** Coverage questions, dashboard, totals — none of these use Claude.
6. **Token budget scaling.** `max_tokens` in `call_text()` scales with input length rather than blowing SDK defaults.

Reset the meter with `POST /tokens/reset` (not exposed by default — call `llm_client.reset_meter()` in code if needed).
