"""
Suggested-questions engine.

Given a captured Fathom summary, compare it against a question template and
return the items whose signals were NOT found — i.e. the topics the team
didn't cover on the call. Deterministic, keyword-based, and zero-token.

Later steps can layer Claude on top of this (rephrase questions to match the
client's tone, or spot semantically similar signals), but the base version
below is enough to prove value and keep the demo fast.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import yaml

TEMPLATE_PATH = Path("templates/questions/default.yaml")

_PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}


def load_template(path: Optional[Path] = None) -> dict:
    p = path or TEMPLATE_PATH
    if not p.exists():
        return {"items": []}
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {"items": []}


def _covered(summary_lc: str, signals: list) -> Optional[str]:
    """Return the first matching signal, or None if nothing matched."""
    for s in signals or []:
        s = str(s).lower().strip()
        if not s:
            continue
        # Match as substring; short signals ("$", "vs ") are common and useful.
        if s in summary_lc:
            return s
    return None


def analyse(summary: str, template: Optional[dict] = None) -> dict:
    """
    Score a summary against the coverage template. Returns:
      {
        "covered":  [{topic, id, matched}],
        "missing":  [{id, topic, priority, question, why}],
        "coverage_percent": 0..100
      }
    """
    template = template or load_template()
    items = template.get("items", []) or []
    summary_lc = (summary or "").lower()

    covered, missing = [], []
    for item in items:
        matched = _covered(summary_lc, item.get("signals", []))
        if matched:
            covered.append({"id": item["id"], "topic": item["topic"], "matched": matched})
        else:
            missing.append({
                "id": item["id"],
                "topic": item["topic"],
                "priority": item.get("priority", "medium"),
                "question": item.get("question", ""),
                "why": item.get("why", ""),
            })

    # Sort missing by priority so the "asks" are already prioritised.
    missing.sort(key=lambda x: _PRIORITY_RANK.get(x["priority"], 3))

    total = len(items) or 1
    pct = round(100 * len(covered) / total)
    return {"covered": covered, "missing": missing, "coverage_percent": pct}
