"""
Step 1 (Option A) — the capture module.

Fathom records the Zoom call and its own AI produces the summary. Our agent's
only job in Step 1 is to *notice* when a summary arrives and capture it — from
either the folder or the webhook — with clean metadata so later steps can act
on it. Structured payloads and raw transcripts are both handled with zero LLM
calls (flattening / regex / keyword coverage). The one exception is a pasted
script that isn't valid JSON: extract_structured_via_llm turns it into the
same structured shape with a single cached, fast-tier call, so the rest of
the pipeline never has to know the difference.

Downstream steps (extraction, brief, proposal, quote) will subscribe to what
this module captures.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from agent import llm_client, questions

# Fields Fathom / Zapier are known to put the summary text in. Order matters:
# we prefer the AI summary over notes over raw transcript.
SUMMARY_KEYS = [
    "summary", "meeting_summary", "ai_summary", "ai_notes",
    "notes", "meeting_notes", "action_items", "transcript",
]
TITLE_KEYS = ["title", "meeting_title", "topic", "subject", "name"]
ID_KEYS = ["id", "meeting_id", "recording_id", "url", "recording_url"]

# Where captures land. Callers set these once at startup.
CAPTURES_DIR = Path("captures")

# In-memory log so the /activity endpoint can show what just happened without
# re-reading the disk. Newest first, capped at 50.
recent: list = []


def _log(kind: str, ref: str, extra: Optional[dict] = None) -> dict:
    entry = {"at": datetime.utcnow().isoformat(), "kind": kind, "ref": ref}
    if extra:
        entry.update(extra)
    recent.insert(0, entry)
    del recent[50:]
    print(f"[capture] {kind}: {ref}")
    return entry


def _walk_for(payload: dict, keys: list) -> str:
    """Look for `keys` at the top level, then nested under common wrappers."""
    for k in keys:
        v = payload.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    for wrap in ("data", "meeting", "event", "payload"):
        inner = payload.get(wrap) if isinstance(payload, dict) else None
        if isinstance(inner, dict):
            for k in keys:
                v = inner.get(k)
                if isinstance(v, str) and v.strip():
                    return v.strip()
    return ""


# Some automations (a Zapier step that runs the transcript through an LLM
# before it ever reaches us) send a pre-digested call-intelligence object —
# nested sections like meeting/client/project/deliverables/timeline/budget —
# instead of Fathom's own flat summary/transcript field. If enough of these
# sections are present, treat the whole payload as one to flatten rather than
# reporting "no summary field found".
STRUCTURED_MARKER_KEYS = {
    "meeting", "client", "project", "deliverables", "timeline",
    "budget", "next_steps", "risks", "target_audience", "creative_direction",
}


def _is_structured_payload(payload: dict) -> bool:
    if not isinstance(payload, dict):
        return False
    return len(STRUCTURED_MARKER_KEYS & payload.keys()) >= 3


def _flatten_json_values(obj, prefix: str = "") -> list:
    """Render nested dict/list values as 'label: value' lines, recursively,
    so the existing (text-based) coverage engine and brief prompts can work
    on a structured payload without a parallel implementation."""
    lines = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            label = f"{prefix}{k}".replace("_", " ")
            if isinstance(v, (dict, list)):
                lines.extend(_flatten_json_values(v, prefix=f"{label} > "))
            elif v not in (None, "", []):
                lines.append(f"{label}: {v}")
    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, (dict, list)):
                lines.extend(_flatten_json_values(item, prefix=prefix))
            elif item not in (None, ""):
                lines.append(f"{prefix.rstrip('> ')}: {item}")
    return lines


def _flatten_structured_payload(payload: dict) -> str:
    return "\n".join(_flatten_json_values(payload))


def _action_items_from_structured(payload: dict) -> list:
    """next_steps is already a structured, owner-tagged action list — far
    more reliable than regex-scanning free text for one."""
    items = []
    for owner, steps in (payload.get("next_steps") or {}).items():
        for s in steps or []:
            if s:
                items.append({"text": str(s), "link": "", "owner": owner})
    return items


# --------------------------------------------------------------------------
# Script -> structured JSON. Used only when someone pastes a raw script or
# transcript that isn't valid JSON — see /webhook/fathom/script. One cached,
# fast-tier call turns it into the same shape a pre-digested payload would
# already be in, so meeting_type/deliverables/timeline/budget/risks/
# next_steps all come out the far end exactly like the JSON path does.
# --------------------------------------------------------------------------
_EXTRACTION_SYSTEM_PROMPT = """Extract a meeting transcript into compact JSON. Output ONLY the JSON object, no commentary, no markdown fences.

Schema — omit any key with no real signal in the transcript, never invent values:
{"meeting":{"title":str,"meeting_type":"Discovery"|"Internal","purpose":str},
 "client":{"company":str,"primary_contact":str,"industry":str},
 "project":{"name":str,"type":str,"objective":str},
 "target_audience":[{"segment":str,"goal":str}],
 "creative_direction":{"style":str,"description":str,"messaging_themes":[str]},
 "deliverables":[{"name":str,"duration":str,"quantity":str,"status":str}],
 "timeline":{"<label>":"<value>"},
 "budget":{"status":str,"currency":str,"estimated_budget":number|null},
 "competition":{"has_competition":bool,"other_agencies":number,"selection_method":str},
 "client_feedback":{"concerns":[str],"positive_reactions":[str]},
 "risks":[str],"opportunities":[str],
 "next_steps":{"genesis":[str],"client":[str]}}

meeting_type is "Discovery" if any speaker is external (shown with an email
domain in parentheses next to their name, e.g. "Name (company.com)", or is
clearly a client); "Internal" if every speaker is on the same team.

Use short phrases, not sentences. Be terse — this is metadata, not prose."""


def extract_structured_via_llm(text: str) -> Optional[dict]:
    """Turn a raw pasted script into the structured shape above. Returns
    None (caller falls back to the zero-token regex/keyword path) if
    there's no API key or the call fails — never raises."""
    result = llm_client.call_json(_EXTRACTION_SYSTEM_PROMPT, text, tier="fast")
    return result if isinstance(result, dict) else None


# Containers a structured payload is commonly found wrapped inside — our own
# /webhook/fathom response shape ("ok"/"captured"/"key_points") if someone
# pastes it back in, plus the generic wrappers _walk_for already knows about.
WRAPPER_KEYS = ["captured", "key_points", "data", "payload", "event", "result"]


def _find_structured_root(payload: dict, depth: int = 2) -> dict:
    """Return `payload`, or a dict nested up to `depth` levels under one of
    WRAPPER_KEYS, whichever one actually looks like a structured
    call-intelligence payload. Falls back to `payload` unchanged."""
    if _is_structured_payload(payload):
        return payload
    if depth <= 0 or not isinstance(payload, dict):
        return payload
    for key in WRAPPER_KEYS:
        inner = payload.get(key)
        if isinstance(inner, dict):
            found = _find_structured_root(inner, depth - 1)
            if _is_structured_payload(found):
                return found
    return payload


def extract_from_payload(payload: dict) -> dict:
    """Pull the summary + title + a stable id out of a webhook payload.

    Falls back to flattening a structured call-intelligence JSON (no flat
    summary/transcript field, but meeting/client/project/... sections) into
    readable text, and pulls meeting_type + action_items straight from that
    structure — more reliable than inferring them from free text. Also
    unwraps a payload someone accidentally nested under "captured" /
    "key_points" (e.g. reposting our own webhook response)."""
    summary = _walk_for(payload, SUMMARY_KEYS)
    title = _walk_for(payload, TITLE_KEYS)
    external_id = _walk_for(payload, ID_KEYS)
    meeting_type_hint = ""
    action_items: list = []
    structured_root = None

    root = _find_structured_root(payload) if not summary else payload
    if not summary and _is_structured_payload(root):
        structured_root = root
        summary = _flatten_structured_payload(root)
        meeting = root.get("meeting") or {}
        project = root.get("project") or {}
        client = root.get("client") or {}
        title = title or project.get("name") or meeting.get("title") or client.get("company") or ""
        mt = str(meeting.get("meeting_type", "")).lower()
        if mt:
            meeting_type_hint = "internal" if "internal" in mt else "discovery_call"
        action_items = _action_items_from_structured(root)

    return {
        "summary": summary,
        "title": title,
        "external_id": external_id,
        "meeting_type_hint": meeting_type_hint,
        "action_items": action_items,
        "structured_root": structured_root,
    }


def fingerprint(payload_or_id: object) -> str:
    """A stable hash used for idempotency. Fathom retries; we don't want dupes."""
    if isinstance(payload_or_id, str) and payload_or_id:
        return hashlib.sha256(f"id:{payload_or_id}".encode()).hexdigest()
    if isinstance(payload_or_id, dict):
        ext = _walk_for(payload_or_id, ID_KEYS)
        if ext:
            return hashlib.sha256(f"id:{ext}".encode()).hexdigest()
        canon = json.dumps(payload_or_id, sort_keys=True, default=str)
        return hashlib.sha256(canon.encode()).hexdigest()
    return hashlib.sha256(str(payload_or_id).encode()).hexdigest()


# Idempotency memory. Fingerprint -> capture filename. Persists for the process
# lifetime; on restart we re-scan the captures dir to rebuild it.
_seen: dict = {}


def _rebuild_seen() -> None:
    _seen.clear()
    for p in CAPTURES_DIR.glob("*.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            fp = data.get("fingerprint")
            if fp:
                _seen[fp] = p.name
        except Exception:
            continue


def _safe_stem(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", s or "capture")[:60] or "capture"


# Fathom labels each speaker turn "0:07 - Name (external-domain.com)" and
# leaves internal/workspace participants unannotated — that's a real,
# observed signal (not a guess) we use to tell a client discovery call
# apart from an internal team meeting.
SPEAKER_LINE_RE = re.compile(
    r"^[ \t]*\d{1,2}:\d{2}(?::\d{2})?[ \t]*-[ \t]*([^(\n]+?)(?:[ \t]*\(([^)]+)\))?[ \t]*$",
    re.MULTILINE,
)

# Fathom inserts detected action items inline in the transcript text, e.g.:
#   ACTION ITEM: Email Mike proposal ... - WATCH: https://fathom.video/...
# The trailing text after the link is often the next speaker's sentence
# running on, so the link is what marks the true end of the action item.
ACTION_ITEM_WITH_LINK_RE = re.compile(
    r"ACTION ITEM:\s*(?P<text>.+?)\s*-\s*WATCH:\s*(?P<link>\S+)",
    re.IGNORECASE | re.DOTALL,
)
ACTION_ITEM_PLAIN_RE = re.compile(r"ACTION ITEM:\s*(?P<text>.+)", re.IGNORECASE)


def extract_action_items(text: str) -> list:
    """Pull Fathom's inline 'ACTION ITEM: ... - WATCH: <link>' markers out of
    a transcript/summary. Falls back to the rest of the line when there's no
    WATCH link attached."""
    text = text or ""
    items, consumed = [], set()
    for m in ACTION_ITEM_WITH_LINK_RE.finditer(text):
        items.append({"text": m.group("text").strip(), "link": m.group("link").strip()})
        consumed.add(m.start())
    for m in ACTION_ITEM_PLAIN_RE.finditer(text):
        if m.start() in consumed:
            continue
        line = m.group("text").splitlines()[0].strip()
        if line:
            items.append({"text": line, "link": ""})
    return items


def extract_participants(text: str) -> list:
    """Distinct speakers from timestamped transcript lines, with their email
    domain if Fathom annotated one (external guests only)."""
    seen = {}
    for m in SPEAKER_LINE_RE.finditer(text or ""):
        name = m.group(1).strip()
        domain = (m.group(2) or "").strip().lower()
        if name and name not in seen:
            seen[name] = domain
    return [{"name": n, "domain": d} for n, d in seen.items()]


def classify_meeting_type(participants: list) -> str:
    """'discovery_call' if any participant carries an external email domain
    (a client/guest), otherwise 'internal'."""
    return "discovery_call" if any(p["domain"] for p in participants) else "internal"


# Business-relevant sections to surface as "key points" when the payload is
# already structured — everything except pure pipeline bookkeeping (metadata
# about who processed the call and when isn't a key point of the meeting).
KEY_POINT_SECTIONS = [
    "meeting", "client", "project", "target_audience", "creative_direction",
    "deliverables", "timeline", "budget", "competition", "client_feedback",
    "risks", "opportunities", "next_steps", "ai_summary", "crm",
]


def _key_points_from_structured(payload: dict) -> dict:
    return {k: payload[k] for k in KEY_POINT_SECTIONS if k in payload}


def _key_points_from_transcript(meeting_type: str, participants: list,
                                action_items: list, coverage: Optional[dict]) -> dict:
    """When there's no structured payload to re-surface, distill what we
    could actually pull out of the free-text transcript — not the raw text
    itself, which is what 'key points' is meant to replace."""
    key_points = {
        "meeting_type": meeting_type,
        "participants": [p["name"] for p in participants],
        "action_items": [a["text"] for a in action_items],
    }
    if coverage:
        key_points["topics_covered"] = [c["topic"] for c in coverage.get("covered", [])]
        key_points["open_questions"] = [
            {"topic": m["topic"], "question": m["question"]}
            for m in coverage.get("missing", [])
        ]
    return key_points


def _key_points_is_thin(key_points: Optional[dict]) -> bool:
    """True if key_points has no real signal beyond the bookkeeping
    meeting_type field — the shape a transient extraction failure falls
    back to. Used so a dedup hit doesn't trap every future retry behind
    one bad first attempt forever."""
    if not key_points:
        return True
    meaningful = {k: v for k, v in key_points.items() if k != "meeting_type"}
    return not any(meaningful.values())


def save_capture(source: str, summary: str, title: str = "",
                 external_id: str = "", raw: Optional[dict] = None,
                 meeting_type_hint: str = "", extra_action_items: Optional[list] = None) -> dict:
    """
    Store a Fathom summary as a capture. Returns a small record describing
    what was saved (or was already there, if we've seen this one before).

    meeting_type_hint / extra_action_items let a caller that already knows
    the answer (a structured call-intelligence payload names its own
    meeting_type and next_steps) skip the text-based inference below, which
    only has transcript speaker lines and inline markers to go on.
    """
    fp = fingerprint(external_id or {"s": summary, "t": title})
    if fp in _seen:
        # Fathom retries send identical content, so this path isn't rare —
        # it should return the same useful key_points as the original
        # capture, not just a bare "yep, saw this already" marker.
        existing_name = _seen[fp]
        existing: dict = {}
        try:
            existing = json.loads((CAPTURES_DIR / existing_name).read_text(encoding="utf-8"))
        except Exception:
            pass
        if not _key_points_is_thin(existing.get("key_points")):
            return _log("dedup", existing_name, {
                "fingerprint": fp,
                "title": existing.get("title", ""),
                "meeting_type": existing.get("meeting_type", ""),
                "key_points": existing.get("key_points", {}),
            })
        # The cached capture came from a transient extraction failure (e.g.
        # a one-off LLM hiccup) that fell back to an empty result. Don't
        # trap every future retry with identical content behind that bad
        # first attempt — fall through and reprocess as if this were new.

    CAPTURES_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    fname = f"{stamp}__{_safe_stem(title or external_id or 'capture')}.json"

    participants = extract_participants(summary)
    meeting_type = meeting_type_hint or classify_meeting_type(participants)
    action_items = extract_action_items(summary) + (extra_action_items or [])
    # The client-discovery checklist (budget, decision-makers, audience...)
    # doesn't apply to an internal team meeting — skip it there rather than
    # surface nonsense "ask the client about their budget" prompts.
    coverage = questions.analyse(summary) if meeting_type == "discovery_call" else None

    # "Key points" is the curated, human-facing view of what the call was
    # about — a structured payload's own sections re-surfaced as-is, or (for
    # a plain transcript) whatever we could actually distill out of it.
    if _is_structured_payload(raw or {}):
        key_points = _key_points_from_structured(raw)
    else:
        key_points = _key_points_from_transcript(meeting_type, participants, action_items, coverage)

    record = {
        "captured_at": datetime.utcnow().isoformat(),
        "source": source,                     # "webhook" | "folder"
        "external_id": external_id,
        "title": title,
        "summary": summary,
        "meeting_type": meeting_type,          # "discovery_call" | "internal"
        "participants": participants,
        "action_items": action_items,
        "key_points": key_points,
        "coverage": coverage,
        "fingerprint": fp,
        "raw_payload_sample": (raw or {}) if source == "webhook" else None,
    }
    (CAPTURES_DIR / fname).write_text(json.dumps(record, indent=2), encoding="utf-8")
    _seen[fp] = fname
    return _log("captured", fname, {"source": source, "title": title,
                                     "meeting_type": meeting_type,
                                     "key_points": key_points,
                                     "chars": len(summary), "fingerprint": fp})
