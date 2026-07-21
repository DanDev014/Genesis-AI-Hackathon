"""
Step 1 (Option A) — the capture module.

Fathom records the Zoom call and its own AI produces the summary. Our agent's
only job in Step 1 is to *notice* when a summary arrives and capture it — from
either the folder or the webhook — with clean metadata so later steps can act
on it. No LLM call happens here. That's deliberate: it keeps Step 1 free of
tokens and easy to reason about.

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

from agent import questions

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


def extract_from_payload(payload: dict) -> dict:
    """Pull the summary + title + a stable id out of a webhook payload."""
    return {
        "summary": _walk_for(payload, SUMMARY_KEYS),
        "title": _walk_for(payload, TITLE_KEYS),
        "external_id": _walk_for(payload, ID_KEYS),
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


def save_capture(source: str, summary: str, title: str = "",
                 external_id: str = "", raw: Optional[dict] = None) -> dict:
    """
    Store a Fathom summary as a capture. Returns a small record describing
    what was saved (or was already there, if we've seen this one before).
    """
    fp = fingerprint(external_id or {"s": summary, "t": title})
    if fp in _seen:
        return _log("dedup", _seen[fp], {"fingerprint": fp})

    CAPTURES_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    fname = f"{stamp}__{_safe_stem(title or external_id or 'capture')}.json"
    # Run coverage analysis: which template questions are already answered?
    coverage = questions.analyse(summary)
    record = {
        "captured_at": datetime.utcnow().isoformat(),
        "source": source,                     # "webhook" | "folder"
        "external_id": external_id,
        "title": title,
        "summary": summary,
        "coverage": coverage,
        "fingerprint": fp,
        "raw_payload_sample": (raw or {}) if source == "webhook" else None,
    }
    (CAPTURES_DIR / fname).write_text(json.dumps(record, indent=2), encoding="utf-8")
    _seen[fp] = fname
    return _log("captured", fname, {"source": source, "title": title,
                                     "chars": len(summary), "fingerprint": fp})
