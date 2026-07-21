"""
Document renderer.

- HTML always works (pure Jinja2, zero native deps).
- PDF works if WeasyPrint is installed. WeasyPrint needs Pango/Cairo on
  Windows, which can be fiddly, so PDF is optional — the HTML route can be
  printed to PDF from any browser and looks identical.

Public API:
    render_proposal_html(data) -> str
    render_quote_html(data)    -> str
    render_pdf(html) -> bytes | None    (None if WeasyPrint isn't available)
"""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from agent import brand as brand_mod

TEMPLATES_DIR = Path("templates")


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True, lstrip_blocks=True,
    )


def _defaults_for_proposal(p: dict) -> dict:
    """Fill in the fields the template expects, so callers can pass a minimal dict."""
    today = date.today().isoformat()
    p = dict(p)
    p.setdefault("number", "0001")
    p.setdefault("date", today)
    p.setdefault("title", "Untitled proposal")
    p.setdefault("status", "draft")
    for key in ("objectives", "scope_items", "deliverables"):
        p.setdefault(key, [])
    p.setdefault("summary", "")
    p.setdefault("approach", "")
    p.setdefault("timeline", "")
    p.setdefault("client_name", "")
    p.setdefault("client_company", "")
    return p


def _defaults_for_quote(q: dict) -> dict:
    today = date.today()
    q = dict(q)
    q.setdefault("number", "0001")
    q.setdefault("date", today.isoformat())
    q.setdefault("title", "Untitled quotation")
    q.setdefault("status", "draft")
    q.setdefault("currency", "USD")
    q.setdefault("line_items", [])
    q.setdefault("client_name", "")
    q.setdefault("client_company", "")
    # Compute totals if the caller didn't.
    for it in q["line_items"]:
        it.setdefault("qty", 1)
        it.setdefault("unit_price", 0)
        it.setdefault("description", "")
        it["amount"] = it.get("amount") or round(it["qty"] * it["unit_price"], 2)
    subtotal = round(sum(i["amount"] for i in q["line_items"]), 2)
    q.setdefault("subtotal", subtotal)
    q.setdefault("tax_rate", 0)
    q["tax"] = round(subtotal * (q["tax_rate"] / 100), 2)
    q.setdefault("total", round(subtotal + q["tax"], 2))
    b = brand_mod.load()
    valid_days = int(b.get("quote_valid_days", 30))
    q.setdefault("valid_until", (today + timedelta(days=valid_days)).isoformat())
    return q


def render_proposal_html(data: dict, template: str = "proposal/default.html") -> str:
    ctx = {"proposal": _defaults_for_proposal(data), "brand": brand_mod.load()}
    return _env().get_template(template).render(**ctx)


def render_quote_html(data: dict, template: str = "quote/default.html") -> str:
    ctx = {"quote": _defaults_for_quote(data), "brand": brand_mod.load()}
    return _env().get_template(template).render(**ctx)


def render_pdf(html: str) -> Optional[bytes]:
    """Render HTML to PDF via WeasyPrint. Returns None if WeasyPrint isn't installed."""
    try:
        from weasyprint import HTML  # type: ignore
    except Exception:
        return None
    return HTML(string=html, base_url=".").write_pdf()
