"""
Simple file-backed storage for proposals and quotes.

Each document is one JSON file on disk. That's it — no database. Later steps
will swap this for Neon; the API here stays the same.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from agent import db

PROPOSALS_DIR = Path("proposals")
QUOTES_DIR = Path("quotes")


def _slug(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", s or "untitled")[:60] or "untitled"


def _next_number(directory: Path) -> str:
    """Return the next serial number by counting existing files."""
    n = len(list(directory.glob("*.json"))) + 1
    return f"{n:04d}"


def _save(directory: Path, kind: str, data: dict) -> dict:
    directory.mkdir(parents=True, exist_ok=True)
    data = dict(data)
    data.setdefault("number", _next_number(directory))
    data.setdefault("created_at", datetime.utcnow().isoformat())
    data.setdefault("status", "draft")
    data["kind"] = kind
    stamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    fname = f"{data['number']}__{stamp}__{_slug(data.get('title', 'untitled'))}.json"
    (directory / fname).write_text(json.dumps(data, indent=2), encoding="utf-8")
    data["id"] = fname
    return data


def _list(directory: Path) -> List[dict]:
    if not directory.exists():
        return []
    out = []
    for p in sorted(directory.glob("*.json"),
                    key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            data["id"] = p.name
            out.append(data)
        except Exception:
            continue
    return out


def _get(directory: Path, doc_id: str) -> Optional[dict]:
    p = directory / doc_id
    if not p.exists():
        return None
    data = json.loads(p.read_text(encoding="utf-8"))
    data["id"] = p.name
    return data


def _update(directory: Path, doc_id: str, patch: dict) -> Optional[dict]:
    data = _get(directory, doc_id)
    if not data:
        return None
    data.update(patch)
    data["updated_at"] = datetime.utcnow().isoformat()
    (directory / doc_id).write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data


# ------------------------------------------------------------------ public
def save_proposal(data: dict) -> dict:
    if db.is_available():
        try: return db.save_proposal(data)
        except Exception as e: print(f"[store] db save_proposal failed, using file: {e}")
    return _save(PROPOSALS_DIR, "proposal", data)


def save_quote(data: dict) -> dict:
    if db.is_available():
        try: return db.save_quote(data)
        except Exception as e: print(f'[store] db save_quote failed, using file: {e}')
    # File-store fallback (computes totals inline).
    # Normalise amounts + total so downstream consumers (QuickBooks, renderer)
    # can trust them without recomputing.
    data = dict(data)
    for it in data.get("line_items", []):
        it.setdefault("qty", 1)
        it.setdefault("unit_price", 0)
        it["amount"] = it.get("amount") or round(it["qty"] * it["unit_price"], 2)
    subtotal = round(sum(i["amount"] for i in data.get("line_items", [])), 2)
    data.setdefault("subtotal", subtotal)
    data.setdefault("total", subtotal)
    data.setdefault("currency", "USD")
    return _save(QUOTES_DIR, "quote", data)


def list_proposals() -> List[dict]:
    if db.is_available():
        rows = db.list_proposals()
        if rows: return rows
    return _list(PROPOSALS_DIR)


def list_quotes() -> List[dict]:
    if db.is_available():
        rows = db.list_quotes()
        if rows: return rows
    return _list(QUOTES_DIR)


def get_proposal(doc_id: str) -> Optional[dict]:
    if db.is_available():
        row = db.get_proposal(doc_id)
        if row: return row
    return _get(PROPOSALS_DIR, doc_id)


def get_quote(doc_id: str) -> Optional[dict]:
    if db.is_available():
        row = db.get_quote(doc_id)
        if row: return row
    return _get(QUOTES_DIR, doc_id)


def update_proposal(doc_id: str, patch: dict) -> Optional[dict]:
    if db.is_available():
        row = db.update_proposal(doc_id, patch)
        if row: return row
    return _update(PROPOSALS_DIR, doc_id, patch)


def update_quote(doc_id: str, patch: dict) -> Optional[dict]:
    if db.is_available():
        row = db.update_quote(doc_id, patch)
        if row: return row
    return _update(QUOTES_DIR, doc_id, patch)
