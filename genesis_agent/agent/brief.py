"""
Brief generation.

Turns a Fathom summary (plus its coverage report) into a short, editable
project brief — the "single source of truth" the deck asks for.

Runs through llm_client so it's Haiku by default, cached, and metered.
Falls back to a deterministic template if there's no API key or the call
fails. Clarity score is coverage_percent — not another LLM call.
"""
from __future__ import annotations

from typing import Optional

from agent import llm_client, questions

SYSTEM_PROMPT = """You are Genesis Digital Factory's project briefing agent.
You read a Fathom summary of a client discovery call and produce a concise
internal project brief. This is the single source of truth the team will
share before any creative work starts.

Respond with markdown, not JSON. Keep it under 220 words. Use these
sections in this order:

## Client & context
## Objectives
## Scope & deliverables
## Timeline
## Budget signal
## Risks & open questions

Rules:
- Do not invent budget numbers or people not in the summary.
- If a section has no signal in the source, write "Not yet established."
- Every line should be actionable — no filler."""

INTERNAL_SYSTEM_PROMPT = """You are Genesis Digital Factory's project briefing agent.
You read a Fathom transcript of an INTERNAL team meeting (no client on the
call) and produce a short recap for people who weren't there.

Respond with markdown, not JSON. Keep it under 180 words. Use these
sections in this order:

## What was discussed
## Decisions made
## Action items (owner — task)
## Open questions

Rules:
- Do not invent decisions or owners not in the transcript.
- If a section has no signal in the source, write "Not yet established."
- Every line should be actionable — no filler."""


def generate_brief(summary: str, client_company: str = "",
                   client_name: str = "", meeting_type: str = "discovery_call",
                   action_items: Optional[list] = None) -> dict:
    """
    Return {"content": markdown, "clarity_score": 0-100, "mode": "live|mock|template"}.

    For a discovery call, clarity_score reuses the coverage engine — no
    separate LLM call. The client-discovery checklist (budget,
    decision-makers, etc.) doesn't apply to an internal meeting, so that
    path scores on whether the transcript yielded concrete action items
    instead.
    """
    action_items = action_items or []

    if meeting_type == "internal":
        score = 100.0 if action_items else 40.0
        items_block = "\n".join(
            f"- {a['text']}" + (f" (watch: {a['link']})" if a.get("link") else "")
            for a in action_items
        ) or "- None explicitly flagged in the transcript."
        user = f"""Meeting: {client_company or client_name or "Internal team meeting"}
Fathom transcript:
---
{summary}
---

Action items Fathom already flagged:
{items_block}

Write the recap now."""
        text = llm_client.call_text(INTERNAL_SYSTEM_PROMPT, user, tier="fast")
        if text:
            return {"content": text, "clarity_score": score, "mode": llm_client.mode()}
        return {
            "content": _template_internal_recap(summary, action_items),
            "clarity_score": score,
            "mode": "template",
        }

    coverage = questions.analyse(summary)
    score = float(coverage.get("coverage_percent", 0))

    user = f"""Client: {client_company or client_name or "Unknown"}
Fathom summary:
---
{summary}
---

Coverage of Genesis's template questions in this summary: {score:.0f}%.
Missing topics you should flag as open questions:
{chr(10).join('- ' + m.get('topic', '') for m in coverage.get('missing', [])[:6])}

Write the brief now."""

    text = llm_client.call_text(SYSTEM_PROMPT, user, tier="fast")
    if text:
        return {"content": text, "clarity_score": score, "mode": llm_client.mode()}

    # Deterministic fallback — still useful when the API key isn't set.
    return {
        "content": _template_brief(summary, client_company, client_name, coverage),
        "clarity_score": score,
        "mode": "template",
    }


def _template_brief(summary: str, company: str, name: str, coverage: dict) -> str:
    covered = ", ".join(c["topic"] for c in coverage.get("covered", [])[:5]) or "—"
    missing = coverage.get("missing", [])[:5]
    open_qs = "\n".join(f"- **{m['topic']}** — {m.get('question', '')}" for m in missing) or "- None flagged."
    return f"""## Client & context
{company or name or "Client"} — see attached Fathom summary.

## Objectives
Extracted from the discovery call. Refine with the client on the next touch.

## Scope & deliverables
Preliminary. To be confirmed after the internal decision meeting.

## Timeline
As stated in the discovery call. Confirm hard dates in next call.

## Budget signal
As referenced in the discovery call. Confirm ceiling and preferred payment terms.

## Risks & open questions
Topics already covered on the call: {covered}.
The team should ask on the next touch:
{open_qs}

_Auto-generated fallback brief. Score {int(coverage.get('coverage_percent', 0))}% based on template coverage._
"""


def _template_internal_recap(summary: str, action_items: list) -> str:
    items = "\n".join(
        f"- {a['text']}" + (f" (watch: {a['link']})" if a.get("link") else "")
        for a in action_items
    ) or "- None explicitly flagged in the transcript."
    return f"""## What was discussed
See attached Fathom transcript.

## Decisions made
Not yet established.

## Action items (owner — task)
{items}

## Open questions
Not yet established.

_Auto-generated fallback recap — no LLM call made._
"""
