"""
Folder-based intake for Fathom summaries.

Fathom (or a Zapier zap in front of it) drops a summary file into `inbox/`.
The watcher notices, hands it to `capture.save_capture()`, moves the original
to `processed/`, and moves on. No LLM call happens here.

Supported drop-in formats:
  .md   Markdown-formatted summary (Fathom's usual export)
  .txt  Plain text
  .json Fathom / Zapier JSON payload with a summary field
"""
from __future__ import annotations

import asyncio
import json
import shutil
from datetime import datetime
from pathlib import Path

from agent import capture

INBOX = Path("inbox")
PROCESSED = Path("processed")
POLL_SECONDS = 3


def _read_summary(path: Path) -> dict:
    """
    Return {'summary': ..., 'title': ..., 'external_id': ..., 'raw': ...} from a file drop.

    For .md and .txt we take the whole text as the summary and use the filename
    (minus extension) as the title. For .json we use the same shape-tolerant
    extractor as the webhook so both paths behave identically.
    """
    raw = path.read_text(encoding="utf-8", errors="ignore")
    if path.suffix.lower() == ".json":
        try:
            payload = json.loads(raw)
            parts = capture.extract_from_payload(payload)
            parts["raw"] = payload
            return parts
        except Exception:
            pass
    return {"summary": raw.strip(), "title": path.stem, "external_id": path.name, "raw": None}


def _process_one(path: Path) -> None:
    try:
        parts = _read_summary(path)
        if not parts.get("summary"):
            capture._log("skipped_empty", path.name)
        else:
            capture.save_capture(
                source="folder",
                summary=parts["summary"],
                title=parts.get("title", "") or path.stem,
                external_id=parts.get("external_id", "") or path.name,
                raw=parts.get("raw"),
            )
        # Move the original either way, so we don't scan it again on the next tick.
        stamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        target = PROCESSED / path.name
        if target.exists():
            target = PROCESSED / f"{stamp}__{path.name}"
        shutil.move(str(path), str(target))
    except Exception as exc:
        capture._log("error", path.name, {"error": str(exc)})


async def watch_loop() -> None:
    for d in (INBOX, PROCESSED, capture.CAPTURES_DIR):
        d.mkdir(parents=True, exist_ok=True)
    capture._rebuild_seen()
    capture._log("watcher_started", str(INBOX),
                 {"poll_seconds": POLL_SECONDS, "known_captures": len(capture._seen)})

    seen_stable: dict = {}
    while True:
        try:
            for p in sorted(INBOX.iterdir()):
                if not p.is_file():
                    continue
                if p.suffix.lower() not in (".md", ".txt", ".json"):
                    continue
                mtime = p.stat().st_mtime
                if seen_stable.get(p) != mtime:
                    seen_stable[p] = mtime
                    continue
                _process_one(p)
                seen_stable.pop(p, None)
        except Exception as exc:
            capture._log("loop_error", "-", {"error": str(exc)})
        await asyncio.sleep(POLL_SECONDS)
