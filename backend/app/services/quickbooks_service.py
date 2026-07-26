"""
QuickBooks Online integration — translates one of our quotes into a
QuickBooks "Estimate" and either fabricates a response (simulated mode,
the default) or actually posts it to Intuit's sandbox API.

Ported from genesis_agent/agent/quickbooks.py (a separate prototype
service) and adapted to this app's real Quote/Proposal shapes — see
CHANGES.md for the field-mapping notes. Two known shortcuts carried over
unsolved from that prototype, not introduced here:

1. `ItemRef.value` / `CustomerRef.value` don't map to real QuickBooks
   Item/Customer ids — there's no such mapping built yet on either side.
   "SERVICES" / "NEW" only work if your sandbox company has a default
   Services item seeded and is fine creating ad-hoc new customers.
2. `_refresh_access_token()` doesn't persist the new refresh_token Intuit
   returns each time — it keeps reusing the original configured one. Fine
   within a sandbox refresh token's ~100 day validity window, not a real
   token-rotation implementation.

Reference: https://developer.intuit.com/app/developer/qbo/docs/api/accounting/all-entities/estimate
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from flask import current_app

# In-memory access-token cache — refreshes on 401. Process-lifetime only;
# a multi-worker deployment would need a shared cache instead.
_access_token = None


def build_estimate_payload(quote: dict) -> dict:
    """Translate a Quote.to_dict() shape (with its nested `proposal.client`
    block) into QuickBooks' Estimate JSON."""
    proposal = quote.get("proposal") or {}
    client = proposal.get("client") or {}

    valid_days = int(quote.get("validity_days") or 30)
    expiry = (date.today() + timedelta(days=valid_days)).isoformat()

    lines = []
    for item in quote.get("line_items") or []:
        qty = float(item.get("qty", 1))
        unit = float(item.get("unit_price", 0))
        lines.append({
            "DetailType": "SalesItemLineDetail",
            "Amount": round(qty * unit, 2),
            "Description": item.get("item", ""),
            "SalesItemLineDetail": {
                "ItemRef": {
                    "value": item.get("qb_item_id") or "SERVICES",
                    "name": item.get("item", ""),
                },
                "Qty": qty,
                "UnitPrice": unit,
            },
        })

    return {
        "CustomerRef": {
            "value": quote.get("qb_customer_id") or "NEW",
            "name": client.get("company") or client.get("name") or "Customer",
        },
        "TxnDate": date.today().isoformat(),
        "ExpirationDate": expiry,
        "DocNumber": f"Q-{quote.get('quote_id')}",
        "CustomerMemo": {"value": (proposal.get("scope_of_work") or "")[:500]},
        "TotalAmt": quote.get("total", 0),
        "Line": lines,
        "CurrencyRef": {"value": quote.get("currency", "USD")},
    }


def send_estimate(quote: dict) -> dict:
    """
    Returns:
      {"mode": "simulated"|"sandbox", "ok": bool, "payload": ..., "response": ...}
      (or "error" instead of "response" on failure)
    """
    payload = build_estimate_payload(quote)
    mode = current_app.config.get("QUICKBOOKS_MODE", "simulated")

    if mode == "sandbox":
        if not _is_configured():
            return {
                "mode": "sandbox",
                "ok": False,
                "error": ("Sandbox mode selected but env vars are missing. "
                          "Set QUICKBOOKS_CLIENT_ID, QUICKBOOKS_CLIENT_SECRET, "
                          "QUICKBOOKS_REFRESH_TOKEN, and QUICKBOOKS_REALM_ID."),
                "payload": payload,
            }
        try:
            response = _post_to_sandbox(payload)
            return {"mode": "sandbox", "ok": True, "payload": payload, "response": response}
        except Exception as exc:
            return {"mode": "sandbox", "ok": False, "error": str(exc), "payload": payload}

    # Simulated (default). Fabricate a plausible response — nothing leaves
    # the machine.
    fake_id = f"SIM-Q{quote.get('quote_id', '0000')}"
    return {
        "mode": "simulated",
        "ok": True,
        "payload": payload,
        "response": {
            "Estimate": {
                "Id": fake_id,
                "SyncToken": "0",
                "DocNumber": payload["DocNumber"],
                "TotalAmt": payload["TotalAmt"],
                "TxnStatus": "Pending",
                "CustomerRef": payload["CustomerRef"],
            },
            "time": datetime.utcnow().isoformat(),
        },
    }


def _is_configured() -> bool:
    cfg = current_app.config
    return bool(
        cfg.get("QUICKBOOKS_CLIENT_ID") and cfg.get("QUICKBOOKS_CLIENT_SECRET")
        and cfg.get("QUICKBOOKS_REFRESH_TOKEN") and cfg.get("QUICKBOOKS_REALM_ID")
    )


def _post_to_sandbox(payload: dict) -> dict:
    import requests  # imported lazily so simulated mode has no dependency

    cfg = current_app.config
    token = _get_access_token()
    url = f"https://sandbox-quickbooks.api.intuit.com/v3/company/{cfg['QUICKBOOKS_REALM_ID']}/estimate"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    r = requests.post(url, headers=headers, json=payload, timeout=15)
    if r.status_code == 401:
        token = _refresh_access_token()
        headers["Authorization"] = f"Bearer {token}"
        r = requests.post(url, headers=headers, json=payload, timeout=15)
    r.raise_for_status()
    return r.json()


def _get_access_token() -> str:
    global _access_token
    if _access_token is None:
        _access_token = _refresh_access_token()
    return _access_token


def _refresh_access_token() -> str:
    """Exchange the long-lived refresh token for a fresh access token."""
    global _access_token
    import base64
    import requests

    cfg = current_app.config
    creds = base64.b64encode(
        f"{cfg['QUICKBOOKS_CLIENT_ID']}:{cfg['QUICKBOOKS_CLIENT_SECRET']}".encode()
    ).decode()
    r = requests.post(
        "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer",
        headers={
            "Authorization": f"Basic {creds}",
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={"grant_type": "refresh_token", "refresh_token": cfg["QUICKBOOKS_REFRESH_TOKEN"]},
        timeout=15,
    )
    r.raise_for_status()
    _access_token = r.json()["access_token"]
    return _access_token
