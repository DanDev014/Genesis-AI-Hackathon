import hashlib
import hmac
import json
import urllib.error
import urllib.request
from datetime import datetime

from flask import current_app


def dispatch_event(event: str, data: dict) -> None:
    """POST a JSON event to the configured outbound webhook URL.

    Best-effort and silent: a downstream listener being unreachable, or no
    URL being configured at all, should never break the request that
    triggered the event (proposal send, quote status change, ...). Signed
    with HMAC-SHA256 when OUTBOUND_WEBHOOK_SECRET is set, the same way we'd
    expect an inbound webhook to prove it came from us.
    """
    url = current_app.config.get("OUTBOUND_WEBHOOK_URL")
    if not url:
        return

    body = json.dumps({
        "event": event,
        "sent_at": datetime.utcnow().isoformat(),
        "data": data,
    }).encode("utf-8")

    headers = {"Content-Type": "application/json"}
    secret = current_app.config.get("OUTBOUND_WEBHOOK_SECRET")
    if secret:
        signature = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        headers["X-Kora-Signature"] = f"sha256={signature}"

    request = urllib.request.Request(url, data=body, method="POST", headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            if response.status >= 300:
                current_app.logger.warning(
                    "Outbound webhook (%s) responded with status %s", event, response.status
                )
    except (urllib.error.HTTPError, urllib.error.URLError) as exc:
        current_app.logger.warning("Outbound webhook (%s) delivery failed: %s", event, exc)
