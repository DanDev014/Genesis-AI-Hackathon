"""
QuickBooks Online integration.

Two modes, controlled by env vars:

  QUICKBOOKS_MODE=simulated  (default)
    Builds a valid QuickBooks Estimate payload and returns it, plus a mock
    QuickBooks-styled preview URL. Nothing leaves the machine. Perfect for
    demos where a live API call is a risk.

  QUICKBOOKS_MODE=sandbox
    Actually calls Intuit's QuickBooks Online sandbox API. Requires:
      QUICKBOOKS_CLIENT_ID       (from developer.intuit.com)
      QUICKBOOKS_CLIENT_SECRET
      QUICKBOOKS_REFRESH_TOKEN   (obtained via one-time OAuth handshake)
      QUICKBOOKS_REALM_ID        (the sandbox company id)

The payload shape is identical in both modes, so switching is a one-env-var
change with no code change.

Reference: https://developer.intuit.com/app/developer/qbo/docs/api/accounting/all-entities/estimate
"""
from __future__ import annotations

import os
from datetime import date, timedelta
from typing import Optional

# ------------------------------------------------------------------ config
MODE = os.getenv("QUICKBOOKS_MODE", "simulated").lower()
CLIENT_ID = os.getenv("QUICKBOOKS_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("QUICKBOOKS_CLIENT_SECRET", "")
REFRESH_TOKEN = os.getenv("QUICKBOOKS_REFRESH_TOKEN", "")
REALM_ID = os.getenv("QUICKBOOKS_REALM_ID", "")

SANDBOX_BASE = "https://sandbox-quickbooks.api.intuit.com"
TOKEN_URL = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"

# In-memory access-token cache. Refreshes on 401.
_access_token: Optional[str] = None


def mode() -> str:
    return MODE


def is_configured() -> bool:
    """Sandbox is configured only if all four env vars are present."""
    return bool(CLIENT_ID and CLIENT_SECRET and REFRESH_TOKEN and REALM_ID)


# ------------------------------------------------------------------ payload
def build_estimate_payload(quote: dict) -> dict:
    """
    Translate one of Kora's quote dicts into QuickBooks' Estimate JSON shape.

    The trickiest field is `ItemRef.value` — QuickBooks needs an existing
    Item id. For simulation we pass the item name; for sandbox mode you'd
    replace this with a real mapping (either a lookup table Genesis
    maintains, or a first-time-use "create item" call).
    """
    valid_days = int(quote.get("valid_days", 30))
    txn_date = quote.get("date") or date.today().isoformat()
    expiry = (date.today() + timedelta(days=valid_days)).isoformat()

    lines = []
    for item in quote.get("line_items", []):
        qty = float(item.get("qty", 1))
        unit = float(item.get("unit_price", 0))
        lines.append({
            "DetailType": "SalesItemLineDetail",
            "Amount": round(qty * unit, 2),
            "Description": item.get("description") or item.get("item", ""),
            "SalesItemLineDetail": {
                "ItemRef": {
                    # In sandbox mode this must be a real Item Id from
                    # QuickBooks. For simulation we pass the name and note it.
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
            "name": quote.get("client_company") or quote.get("client_name") or "Customer",
        },
        "TxnDate": txn_date,
        "ExpirationDate": expiry,
        "DocNumber": quote.get("number"),
        "CustomerMemo": {"value": quote.get("title", "")},
        "TotalAmt": quote.get("total", 0),
        "Line": lines,
        "CurrencyRef": {"value": quote.get("currency", "USD")},
    }


# ------------------------------------------------------------------ dispatch
def send_estimate(quote: dict) -> dict:
    """
    Send a Kora quote to QuickBooks.

    Returns a dict of the form:
      {
        "mode":     "simulated" | "sandbox",
        "ok":       bool,
        "payload":  <what would be / was posted>,
        "response": <what QuickBooks returned, or a simulated one>,
        "preview_url": /quickbooks/preview/<quote_id>,  # simulated only
      }
    """
    payload = build_estimate_payload(quote)

    if MODE == "sandbox":
        if not is_configured():
            return {
                "mode": "sandbox",
                "ok": False,
                "error": ("Sandbox mode selected but env vars are missing. "
                          "Set QUICKBOOKS_CLIENT_ID, QUICKBOOKS_CLIENT_SECRET, "
                          "QUICKBOOKS_REFRESH_TOKEN, and QUICKBOOKS_REALM_ID."),
                "payload": payload,
            }
        try:
            resp = _post_to_sandbox(payload)
            return {"mode": "sandbox", "ok": True, "payload": payload, "response": resp}
        except Exception as exc:
            return {"mode": "sandbox", "ok": False,
                    "error": str(exc), "payload": payload}

    # Simulated (default). Fabricate a plausible response.
    fake_qb_id = f"SIM-{quote.get('number', '0000')}"
    return {
        "mode": "simulated",
        "ok": True,
        "payload": payload,
        "response": {
            "Estimate": {
                "Id": fake_qb_id,
                "SyncToken": "0",
                "DocNumber": quote.get("number"),
                "TotalAmt": quote.get("total", 0),
                "TxnStatus": "Pending",
                "CustomerRef": payload["CustomerRef"],
            },
            "time": _now_iso(),
        },
        "preview_url": f"/quickbooks/preview/{quote['id']}",
    }


# ------------------------------------------------------------------ sandbox
def _post_to_sandbox(payload: dict) -> dict:
    """Do the real HTTP call to Intuit's sandbox. Handles token refresh on 401."""
    import requests   # imported lazily so simulated mode has no dependency

    token = _get_access_token()
    url = f"{SANDBOX_BASE}/v3/company/{REALM_ID}/estimate"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    r = requests.post(url, headers=headers, json=payload, timeout=15)
    if r.status_code == 401:
        # Access token expired — refresh once and retry.
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

    creds = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    r = requests.post(
        TOKEN_URL,
        headers={
            "Authorization": f"Basic {creds}",
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={"grant_type": "refresh_token", "refresh_token": REFRESH_TOKEN},
        timeout=15,
    )
    r.raise_for_status()
    _access_token = r.json()["access_token"]
    return _access_token


def _now_iso() -> str:
    from datetime import datetime
    return datetime.utcnow().isoformat()
