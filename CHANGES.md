# Changes — proposal/quote workflow additions

Everything added across this run of sessions, why, and what's still open.
Source docs this work was scoped against: the Fathom webhook memo, the "what's
missing" gap table, and the Tafsiri Execution List (Mike's meeting notes).

---

## 1. Outbound webhook on send

**What**: `backend/app/services/webhook_dispatcher.py` — POSTs a JSON event to
`OUTBOUND_WEBHOOK_URL` whenever a proposal is sent (`proposal.sent`) or a quote's
status transitions to `sent` (`quote.sent`, only on the actual draft→sent change,
not every edit). Signed with HMAC-SHA256 in `X-Kora-Signature` when
`OUTBOUND_WEBHOOK_SECRET` is set. Silently no-ops if the URL isn't configured, and
swallows delivery failures — a dead downstream listener should never break the
send itself.

**Why**: flagged in the gap table as a missing integration point for downstream
automation (Slack pings, Zapier steps, etc.) once something goes out to a client.

**Files**: `webhook_dispatcher.py` (new), `proposal_service.py`
(`send_proposal`), `quote_service.py` (`update_quote`), `config.py`,
`.env.example`.

---

## 2. Job outcome + client feedback ("did we get the job?")

**What**: new `Proposal` columns — `outcome` (`pending`/`won`/`lost`),
`outcome_notes` (free text), `outcome_at`. New `POST /api/proposals/<id>/outcome`.
Deliberately separate from `status` (draft/sent/revised/accepted/rejected), which
only tracks the *document's* lifecycle, not the deal's actual result.

**Why**: the gap table's #1 dashboard-adjacent ask — "did we get the job" needs
its own field because a proposal can sit at `status = sent` indefinitely with no
record of what actually happened.

**Files**: `models/proposal.py`, `services/proposal_service.py`
(`record_outcome`), `routes/proposals.py`, `utils/constants.py`
(`PROPOSAL_OUTCOMES`). Frontend: new `RecordOutcomeModal.vue`, outcome badge +
card on `proposals/[id].vue`, and the matching Nuxt proxy route
`server/api/proposals/[id]/outcome.post.ts`.

Excluded from `to_public_dict()` on purpose — a client viewing their own
proposal via the public share link shouldn't see internal "lost" markings or
notes about them.

---

## 3. Dashboard win-rate fix

**What**: `ReportService.get_dashboard()`'s `win_rate` now computes from
`Proposal.outcome` (won vs. won+lost) instead of `Quote.status`
(accepted/expired).

**Why**: after adding #2, the dashboard was left computing "success rate" from
a document status field that has nothing to do with the new outcome field —
recording an outcome didn't move the number at all.

**Files**: `services/report_service.py` only.

---

## 4. Requirements checklist

**What**: transcript extraction now pulls a distinct `requirements` list — the
client's stated constraints/asks ("needs SSO," "must launch before Black
Friday") — separate from `deliverables` (the things being built/shipped). Stored
on `Proposal.requirements_checklist` as `[{"text", "checked"}, ...]`. Reused the
existing generic `PATCH /api/proposals/<id>` endpoint rather than adding a new
route.

**Why**: explicit ask in both the gap table and the Tafsiri execution list.

**Files**:
- `genesis_agent/agent/capture.py` — extraction schema + `KEY_POINT_SECTIONS`.
- `genesis_agent/agent/main.py` — `_proposal_data_from_key_points()` surfaces it.
- `backend/app/models/proposal.py` — new column, in both `to_dict()` and
  `to_public_dict()` (client can see the same checklist on their read-only page).
- `backend/app/services/proposal_service.py` — `_normalize_requirements()`.
- `frontend/server/api/agent/fathom.post.ts` — passes it through.
- New `frontend/app/components/RequirementsChecklist.vue`.
- `frontend/app/pages/p/[token].vue` — read-only version on the public page.

---

## 5. Real audit trail (user-attributed activity log)

**What**: new `activity_logs` table (`entity_type`, `entity_id`, `user_id`,
`action`, `details` JSONB, `created_at`). Logged from within the same DB
transaction as the action it describes, so the log and the change land — or
roll back — together. Surfaced via `GET /api/proposals/<id>/activity` and an
"Activity" card on the proposal detail page.

**Why**: the dashboard's existing "recent activity" is synthesized from
`created_at` on existing rows — no idea *who* did anything, only ever "created."

**Files**: `models/activity_log.py`, `services/activity_log_service.py` (new),
wired into `proposal_service.py` (create/update/send/outcome/approve) and
`quote_service.py` (create/update/sent-to-quickbooks), `routes/proposals.py`.
Frontend: `server/api/proposals/[id]/activity.get.ts`, activity feed card on
`proposals/[id].vue`.

**Caveat**: required threading `user_id` through several requests that didn't
carry one before, since this backend has no real session auth (see #12's note
on `JWT_SECRET_KEY`). `SendProposalModal.vue`, `RecordOutcomeModal.vue`,
`EditProposalModal.vue`, `RequirementsChecklist.vue`, `EditQuotationModal.vue`
now all send `user_id: authStore.user?.user_id`. Optional server-side — a call
without one just logs `user_id: null` ("System"). Requirements-checklist
toggles send `user_id` too but don't produce a log row (judged too noisy).

---

## 6. AI feedback loop (v1 — logging + prompt context, not fine-tuning)

**What**: the "realistic first version" the original gap doc proposed — "log
outcomes + human edits made to AI drafts, and feed recent examples back into
the prompt as context."
1. **Logging**: `update_proposal` snapshots AI-draftable fields
   (`scope_of_work`, `deliverables_list`, `timeline_milestones`) before a PATCH,
   and — when they actually change — logs an `updated` activity with a
   before/after diff and an `is_ai_edit` flag. New
   `GET /api/proposals/feedback-examples?limit=3` returns recent resolved
   (won/lost) AI-drafted proposals paired with their earliest human-edit diff.
2. **Feeding it back**: `genesis_agent/agent/feedback.py` — fetches that
   endpoint (best-effort, 3s timeout, `[]` on any failure), formats it as a
   calibration block, appended to the extraction system prompt.

**Files**: `proposal_service.py` (diff capture + `feedback_examples()`),
`routes/proposals.py`. `genesis_agent/agent/feedback.py` (new),
`genesis_agent/agent/capture.py` (`extract_structured_via_llm` appends context).

**Caveat**: gated behind `FEEDBACK_API_URL` — unset by default (no-op). Also
needs real data to draw on (a won/lost outcome *and* a human edit on that same
proposal) — will do nothing useful until a few real proposals go through that
full cycle.

---

## 7. Native Fathom webhook — signature verification + auto-classify

**What**: new `POST /webhook/fathom/native` in genesis_agent, alongside the
existing two (`/webhook/fathom` for pre-digested JSON, `/webhook/fathom/script`
for a pasted transcript). This is what Fathom's own dashboard would POST to
automatically:
- **HMAC-SHA256 signature verification**, Svix-style (`webhook-id` /
  `webhook-timestamp` / `webhook-signature` headers, `whsec_...` secret).
  Fails closed: no `FATHOM_WEBHOOK_SECRET` configured, or any header missing,
  means every request is rejected. Unit-tested in isolation (valid sig
  accepted, tampered body rejected, unset secret rejected).
- **`meeting_type` is now optional** — `_capture_payload()` falls through to
  `capture.save_capture()`'s existing participant-domain classifier when the
  caller doesn't supply one.

**Files**: `genesis_agent/agent/main.py` (`_verify_fathom_signature`,
`fathom_webhook_native`, `_capture_payload` refactor), `genesis_agent/.env.example`.

**Still blocked on two things — genuinely, not an oversight:**
1. **The exact JSON field Fathom uses for the transcript** hasn't been
   confirmed against a real payload. `capture.raw_transcript_text()`'s lookup
   list may need one more key once you see one.
2. **The signature scheme hasn't been tested against a real Fathom-signed
   request** — correct per the documented convention, unconfirmed against
   actual output.

**In progress as of this writing**: you registered a webhook.site test URL in
Fathom and had at least one real meeting recorded since. The concrete next
step is retrieving that captured payload and sharing it so both gaps above can
be closed in one pass.

---

## 8. "System sends the client link automatically" — reinterpreted, not built as literally stated

**What Mike's note describes** — a proposal auto-emails itself to the client
the moment it's generated, with no human involved — **was not built.** This
backend has zero approval gate on proposal *sending* specifically (approval
now exists for a different purpose, see #9); building literal auto-send would
mean an AI-guessed scope and price reaching a real client with nobody ever
having looked at it. That tradeoff was surfaced explicitly and you chose not
to go that route.

**What was built instead**:
- `Proposal.share_token` generated **at creation time**, not just on first
  "Send" — the link exists the moment a draft does.
- A `proposal.draft_ready` event fires through the outbound webhook
  dispatcher (#1) the moment a proposal is created — a team notification, not
  a client-facing send.

The actual "Send to client" click is unchanged.

**Files**: `services/proposal_service.py` (`create_proposal`).

---

## 9. Approval gate + QuickBooks integration ported into the real app

**What**: two things, built together because the second needed the first.
1. **Proposal approval** — new `Proposal.approved_at` / `approved_by_user_id`
   columns, `POST /api/proposals/<id>/approve` (one-way, no unapprove). The
   first real "someone reviewed this" gate anywhere in this backend.
2. **QuickBooks**, ported from `genesis_agent/agent/quickbooks.py` (a separate
   prototype, never connected to this app) into
   `backend/app/services/quickbooks_service.py` — builds a QuickBooks
   "Estimate" from a quote, `QUICKBOOKS_MODE=simulated` (default, fabricates a
   response) or `sandbox` (real Intuit sandbox calls, OAuth refresh-token
   exchange included). New `POST /api/quotes/<id>/send-to-quickbooks`.

**The gate**: `QuoteService.send_to_quickbooks()` checks
`ProposalService.is_approved(quote.proposal_id)` first — 409 if not approved,
**no override, no bypass.** Enforced server-side.

**Caveat**: no role check on *who* can approve — any logged-in user can, since
this backend doesn't enforce roles server-side at all yet.

**Two shortcuts carried over from the prototype, not introduced here**:
- `ItemRef.value` / `CustomerRef.value` fall back to `"SERVICES"` / `"NEW"` —
  no real QuickBooks Item/Customer mapping exists on either side.
- `_refresh_access_token()` doesn't persist the new refresh_token Intuit
  returns each call — reuses the configured one. Fine within a sandbox
  token's ~100 day window, not real rotation.

**Frontend bug found and fixed**: the "Send to QuickBooks" button forced
white text unconditionally, which was invisible against the disabled-state's
light grey background — looked like a blank box. Fixed to only force white
text when the button is actually enabled (`quotations/[id].vue`).

**Files**: `models/proposal.py` (approval columns), `models/quote.py`
(`quickbooks_result` JSONB), `services/proposal_service.py`
(`approve_proposal`, `is_approved`), `services/quickbooks_service.py` (new),
`services/quote_service.py` (`send_to_quickbooks`), `routes/proposals.py`,
`routes/quotes.py`, `config.py` (4 `QUICKBOOKS_*` reads — values were already
sitting in `backend/.env`, unused, since nothing read them before). Frontend:
`server/api/proposals/[id]/approve.post.ts`,
`server/api/quotes/[id]/send-to-quickbooks.post.ts`, Approve button + badge on
`proposals/[id].vue`, Send to QuickBooks button + status card on
`quotations/[id].vue`.

---

## 10. Time-to-proposal metric

**What**: new `Proposal.meeting_occurred_at` column (distinct from
`created_at`). `to_dict()` exposes it plus a computed `time_to_proposal_hours`.
Dashboard gets a 5th metric card; shown per-proposal on the detail page too.

**Where the timestamp comes from**: `capture.py`'s `MEETING_TIME_KEYS` lookup
tries common field names against an incoming payload, threaded through
`save_capture()` → `_capture_payload()` → the proposal dict Nuxt/genesis_agent
delivers. Falls back to capture time (basically "now") when none match — which
today is every proposal from the manual-paste flow, since a human pastes right
after the meeting rather than the meeting carrying its own timestamp.

**Why it won't mean much yet**: it'll read close to "how long the paste-to-
generate click took" until real Fathom payloads with real meeting timestamps
flow through #7/#11. The plumbing is ready; the input signal is the piece
still missing.

**Files**: `genesis_agent/agent/capture.py` (`MEETING_TIME_KEYS`,
`_parse_meeting_time`), `genesis_agent/agent/main.py` (threaded through),
`backend/app/models/proposal.py` (column + `time_to_proposal_hours`, naive/
aware-safe subtraction), `backend/app/services/proposal_service.py`
(`_parse_meeting_time`), `backend/app/services/report_service.py`
(`avg_time_to_proposal_hours`). Frontend: `fathom.post.ts`, `dashboard.vue`
(5th metric card), `proposals/[id].vue`.

---

## 11. Native webhook → real Flask records (the missing bridge)

**What**: new `genesis_agent/agent/flask_bridge.py`. Before this, when
`/webhook/fathom/native` (#7) processed a meeting, it only wrote into
genesis_agent's own local store (`db.py`'s raw SQL insert) — an orphaned,
duplicate row nothing else ever looks at (see "Important discovery" below).
Nothing connected an automated webhook to a real, visible record in the app.
Now:
- **Internal meeting** → `deliver_internal_meeting()` calls Flask's real
  `POST /proposals` then `POST /quotes` — same shape Nuxt's
  `handleInternalMeeting()` already produces for the manual-paste flow, just
  triggered with no human involved.
- **Discovery call** → `deliver_discovery_call()` calls `POST /summaries`,
  mirroring Nuxt's `handleDiscoveryMeeting()`.
- Both resolve a client first via `find_or_create_client()` — tries
  `POST /clients`, and on the 409 "already exists," falls back to a
  company-name search.

`_capture_payload()` took a `deliver` param (`"local"` default, unchanged for
the other two endpoints; `"flask"` only for the native one).

**Verified end-to-end against the real backend** (with `FLASK_API_URL` /
`GENESIS_SYSTEM_USER_ID` set for the test) — a simulated internal meeting
produced a real client + proposal (share token, draft status, everything
#1–#10 expect) + quote; a simulated discovery call produced a real summary.
**This created real test rows**: client "Acme Test Co" (proposal #10059,
quote #10055), client "Beta Test Co" (summary #36) — still sitting in the
database as of this writing, flagged to you, not yet cleaned up either way.

**Side effect**: fixes the duplicate-write problem (below) for meetings
coming through the native webhook specifically, since it now writes to Flask
directly instead of genesis_agent's local store. The existing
`/webhook/fathom/script` path (what `kora-ai.vue` actually uses today) is
untouched and still has the duplicate-write issue.

**Three shortcuts, consistent with existing patterns in this codebase**:
1. `GENESIS_SYSTEM_USER_ID` (env var) — no human is logged in during an
   automated webhook, so every record gets attributed to whichever real user
   id you configure. No synthetic "AI agent" account exists.
2. Placeholder email `<slugified-company>@unknown.local` when a transcript
   doesn't state one (the common case) — the *exact* fallback genesis_agent's
   own `db.py` already used for its local writes, just now visible in real
   client records.
3. Client dedup is approximate (company-name search, not a true by-email
   lookup — Flask has no such endpoint).

**Files**: `genesis_agent/agent/flask_bridge.py` (new),
`genesis_agent/agent/main.py` (`deliver` param), `genesis_agent/.env.example`
(`FLASK_API_URL`, `GENESIS_SYSTEM_USER_ID`).

**Reminder**: this only activates in production once #7's remaining blockers
clear — registering the real webhook with Fathom and confirming the
transcript field. Built and tested; nothing calls it for real traffic yet.

---

## Important discovery, still unfixed — likely creating duplicate data right now

genesis_agent and backend point at the **same Neon database** (confirmed —
identical `DATABASE_URL`s), and genesis_agent's own `agent/db.py` does a raw
SQL `INSERT INTO proposals` directly into that shared database, completely
independent of anything Flask/Nuxt does.

Today's manual-paste internal-meeting flow:
1. `kora-ai.vue` → Nuxt's `/api/agent/fathom` → genesis_agent's
   `/webhook/fathom/script`.
2. genesis_agent extracts the transcript **and immediately writes its own
   proposal + quote row straight into the shared tables**
   (`_internal_meeting_deliverables()` → `store.save_proposal()`), using its
   own client lookup (`_client_id_for()` by company/name/email).
3. Nuxt then **separately POSTs to Flask's own `/api/proposals`**, inserting
   a **second** proposal + quote row — the one the frontend actually shows.

Step 2's row is never referenced again — an orphan that still counts in
`Proposal.query.count()`, the dashboard's pipeline breakdown, win rate,
`meetings_processed`, and the new time-to-proposal average. **Every
internal-meeting proposal generated through `kora-ai.vue` to date likely has
a duplicate**, possibly with a duplicate/junk client too.

**Not fixed** — needs a decision: should genesis_agent stop writing to the DB
entirely when running behind Flask (it's now purely an extraction engine in
this architecture), or should the two be reconciled differently? #11 fixes
this for the *native webhook* path specifically; the paste-flow path (the one
actually in use today) still has it.

---

## Setup still required (not code — things only you can do)

**1. Apply the schema changes to Neon.** No migrations tooling is wired up in
this repo (Flask-Migrate is `init_app`'d but `flask db init` was never run):

```sql
ALTER TABLE proposals
  ADD COLUMN outcome VARCHAR(20) NOT NULL DEFAULT 'pending',
  ADD COLUMN outcome_notes TEXT,
  ADD COLUMN outcome_at TIMESTAMPTZ,
  ADD COLUMN requirements_checklist JSONB,
  ADD COLUMN approved_at TIMESTAMPTZ,
  ADD COLUMN approved_by_user_id INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
  ADD COLUMN meeting_occurred_at TIMESTAMPTZ;

ALTER TABLE quotes
  ADD COLUMN quickbooks_result JSONB;

CREATE TABLE activity_logs (
  activity_log_id SERIAL PRIMARY KEY,
  entity_type VARCHAR(20) NOT NULL,
  entity_id INTEGER NOT NULL,
  user_id INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
  action VARCHAR(40) NOT NULL,
  details JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

As of this session this has already been run against the real database (we
hit and resolved the "column does not exist" errors live) — included here for
anyone else's environment that hasn't caught up yet.

**2. Env vars — backend** (`backend/.env`):
- `OUTBOUND_WEBHOOK_URL` / `OUTBOUND_WEBHOOK_SECRET` — optional, no-op if unset.
- `RESEND_API_KEY` / `MAIL_FROM` / `PUBLIC_APP_URL` — needed for "Send to
  client" email.
- `QUICKBOOKS_MODE` / `QUICKBOOKS_CLIENT_ID` / `QUICKBOOKS_CLIENT_SECRET` /
  `QUICKBOOKS_REFRESH_TOKEN` / `QUICKBOOKS_REALM_ID` — already present, now
  actually wired up. Double-check `QUICKBOOKS_MODE` before approving/sending
  a real quote — `sandbox` makes a real call to Intuit.

**3. Env vars — genesis_agent** (`genesis_agent/.env`):
- `FEEDBACK_API_URL` — turns on the AI feedback loop. Unset = no-op.
- `FATHOM_WEBHOOK_SECRET` — the `whsec_...` from registering
  `/webhook/fathom/native` with Fathom. Unset = endpoint rejects everything.
- `FLASK_API_URL` + `GENESIS_SYSTEM_USER_ID` — needed for #11's bridge.
  Without both, the native webhook still verifies/extracts but can't deliver
  anywhere.

**4. Python version.** Backend needs Python 3.11+ (`datetime.UTC` in
`summary_service.py`). A mismatched local interpreter (e.g. a conda env
pinned to 3.8) will fail at import with `cannot import name 'UTC'`.

**5. Registering the real Fathom webhook** — full step-by-step:
   1. Register a webhook.site URL in Fathom first (Settings → API Access →
      Add Webhook), trigger/wait for a real meeting, inspect the captured
      payload — confirms the transcript field name and the signature header
      shape before pointing real traffic at our own endpoint.
   2. Expose genesis_agent publicly (a tunnel like `ngrok http 8000` for
      testing, or a real deployment) — Fathom's servers can't reach
      `localhost`.
   3. Register the real webhook in Fathom pointing at
      `<public-url>/webhook/fathom/native`, save the `whsec_...` secret it
      gives you.
   4. Set `FATHOM_WEBHOOK_SECRET`, `FLASK_API_URL`, `GENESIS_SYSTEM_USER_ID`
      in `genesis_agent/.env`, restart genesis_agent.
   5. Make sure genesis_agent and Flask can actually reach each other over
      the network (not just both "running").
   6. Trigger a real meeting, check genesis_agent's logs for the incoming
      POST + signature pass, check Flask/the dashboard for the new
      proposal/summary appearing.

   **Status**: a webhook.site test URL was registered and at least one real
   meeting has since been recorded in Fathom. Next concrete step: retrieve
   that captured payload from webhook.site and share it so the transcript
   field name and signature format can be confirmed.

---

## Still open — not started, not code, or blocked on you

| Item | Note |
|---|---|
| WhatsApp delivery | Dropped — email + shareable link only. WhatsApp needs an application process there wasn't time for. |
| Literal "auto-send, zero human review" | Deliberately not built — see #8. Human "Send" click remains the review gate. |
| "Design artifact" quality bar | Branded templates exist; subjective call for Mike, not a checkbox. |
| Duplicate proposal/quote writes on the manual-paste flow | See "Important discovery" — #11 only fixed this for the native-webhook path, not the one in daily use today. |
| Role-based permissions | Anyone logged in can approve, send, record outcomes — no "must be a manager" check anywhere. |
| Real server-side session auth | `JWT_SECRET_KEY` is configured but nothing issues or verifies a token; the frontend's session is a plain, unsigned cookie the backend trusts as-is. |
| Database migrations tooling | Every schema change so far has been a manual `ALTER TABLE` run by hand against Neon. |

## Concerns raised, not code tasks

- **AI-summary trust**: already mitigated in `capture.py` — never trusts a
  source's own AI-generated summary, always re-extracts from the raw
  transcript.
- **"No copy, no paste" rule**: needs clarifying with Mike — unclear if it
  means transcript security, client-side data, or something else.
- **Pitching workshop**: not a code task; a next step for the team.
