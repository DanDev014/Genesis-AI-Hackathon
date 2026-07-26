"""
AI feedback loop — "realistic first version" per the gap doc: log outcomes
+ human edits made to AI drafts, then feed recent examples back into the
extraction prompt as context. Not model fine-tuning — just giving the LLM a
few real "here's what the team corrected, and what happened" examples to
calibrate against on the next extraction.

The actual logging (activity log, outcome field) lives in the Flask
backend, which owns that data. This module only reads it back, best-effort:
if FEEDBACK_API_URL is unset or the backend is unreachable, extraction
proceeds exactly as before with zero added latency or risk.
"""
from __future__ import annotations

import os
from typing import Optional

FEEDBACK_API_URL = os.getenv("FEEDBACK_API_URL", "")


def fetch_recent_examples(limit: int = 3) -> list:
    """GET the Flask backend's /proposals/feedback-examples. Returns []
    on any failure (unset URL, network error, bad response) — this must
    never block or break a transcript extraction."""
    if not FEEDBACK_API_URL:
        return []
    try:
        import requests  # already a dependency (QuickBooks sandbox calls)
        resp = requests.get(FEEDBACK_API_URL, params={"limit": limit}, timeout=3)
        resp.raise_for_status()
        return resp.json().get("examples", []) or []
    except Exception as exc:
        print(f"[feedback] fetch_recent_examples failed (continuing without it): {exc}")
        return []


def format_examples_for_prompt(examples: list) -> str:
    """Render examples as a short block to append to the extraction system
    prompt. Empty string (not appended) if there's nothing to show yet."""
    if not examples:
        return ""

    lines = [
        "\n\nRecent team corrections to AI-drafted proposals, for calibration "
        "— what the team actually changed, and whether the deal was won or "
        "lost. Use these to judge tone/detail level; never copy their "
        "specifics into an unrelated transcript."
    ]
    for i, example in enumerate(examples, 1):
        outcome = example.get("outcome", "unknown")
        lines.append(f"- Example {i} (outcome: {outcome}):")
        human_edit = example.get("human_edit")
        if human_edit:
            for field, change in human_edit.items():
                before = str(change.get("before", ""))[:160]
                after = str(change.get("after", ""))[:160]
                lines.append(f"  team corrected {field}: {before!r} -> {after!r}")
        else:
            scope = str(example.get("scope_of_work", ""))[:200]
            if scope:
                lines.append(f"  final scope (no edits needed): {scope!r}")

    return "\n".join(lines)


def build_context_suffix(limit: int = 3) -> str:
    """One call for capture.py to use: fetch + format in one step."""
    return format_examples_for_prompt(fetch_recent_examples(limit))
