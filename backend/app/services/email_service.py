import json
import urllib.error
import urllib.request

from flask import current_app

from app.exceptions import EmailDeliveryError


def _brand_email_html(heading: str, message: str, cta_label: str, cta_url: str) -> str:
    """Minimal, fully inline-styled HTML — email clients don't reliably
    render external stylesheets or modern CSS, so nothing here depends on
    a <style> block or anything beyond basic inline attributes."""
    safe_message = (message or "").replace("\n", "<br />")
    return f"""
<div style="font-family:Arial,Helvetica,sans-serif;background:#f5f5f5;padding:32px 0;">
  <div style="max-width:520px;margin:0 auto;background:#ffffff;border-radius:12px;overflow:hidden;border:1px solid #e5e5e5;">
    <div style="background:#0a0a0a;padding:24px 32px;">
      <span style="color:#e0b818;font-weight:700;font-size:18px;">Tafsiri</span>
    </div>
    <div style="padding:32px;">
      <h1 style="font-size:20px;color:#111111;margin:0 0 16px;">{heading}</h1>
      <p style="font-size:14px;line-height:1.6;color:#444444;margin:0 0 24px;">{safe_message}</p>
      <a href="{cta_url}" style="display:inline-block;background:#e0b818;color:#111111;font-weight:700;text-decoration:none;padding:12px 24px;border-radius:8px;font-size:14px;">{cta_label}</a>
      <p style="font-size:12px;color:#999999;margin:24px 0 0;">Or copy this link: {cta_url}</p>
    </div>
  </div>
</div>
""".strip()


def send_email(to_email, subject: str, heading: str, message: str,
                cta_label: str, cta_url: str) -> None:
    """Send a branded transactional email via Resend's HTTP API.

    to_email: a single address, or a list of them (e.g. sending one
    discovery-call summary to several team members at once).

    Uses urllib (stdlib) instead of `requests` — this is the only outbound
    HTTP call the backend makes, so it isn't worth a new dependency.
    Raises EmailDeliveryError if unconfigured or the send fails; callers
    decide how that surfaces to the user."""
    api_key = current_app.config.get("RESEND_API_KEY")
    if not api_key:
        raise EmailDeliveryError(
            "Email isn't configured yet — set RESEND_API_KEY."
        )

    recipients = to_email if isinstance(to_email, list) else [to_email]

    body = json.dumps({
        "from": current_app.config.get("MAIL_FROM"),
        "to": recipients,
        "subject": subject,
        "html": _brand_email_html(heading, message, cta_label, cta_url),
    }).encode("utf-8")

    request = urllib.request.Request(
        "https://api.resend.com/emails",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            # Cloudflare (which fronts Resend's API) blocks Python urllib's
            # default User-Agent as bot-like — HTTP 403, plain-text body
            # "error code: 1010". A normal-looking one is all it takes to
            # get through; confirmed by reproducing the exact failure and
            # the exact fix directly against the real API.
            "User-Agent": "Tafsiri-Backend/1.0",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            if response.status >= 300:
                raise EmailDeliveryError(
                    f"Resend responded with status {response.status}."
                )
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise EmailDeliveryError(f"Resend rejected the email: {detail}") from exc
    except urllib.error.URLError as exc:
        raise EmailDeliveryError(f"Couldn't reach Resend: {exc.reason}") from exc
