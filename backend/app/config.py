import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Neon (like most managed/serverless Postgres) silently drops idle
    # connections. Without pre-ping, the pool hands out dead connections and
    # every request fails with OperationalError until the process restarts.
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
    }

    SECRET_KEY = os.getenv("SECRET_KEY")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")

    # ---------- Transactional email (proposal send) ----------
    RESEND_API_KEY = os.getenv("RESEND_API_KEY")
    MAIL_FROM = os.getenv("MAIL_FROM", "Kora AI <onboarding@resend.dev>")
    # Base URL of the deployed frontend — used to build the public,
    # unauthenticated share link a client clicks from their email.
    PUBLIC_APP_URL = os.getenv("PUBLIC_APP_URL", "http://localhost:3000")

    # ---------- Outbound webhook (proposal/quote sent) ----------
    # Fires a JSON POST at this URL whenever a proposal is sent or a quote
    # transitions to "sent" — e.g. to notify Slack or a Zapier catch hook.
    # Unset means the dispatcher is a no-op.
    OUTBOUND_WEBHOOK_URL = os.getenv("OUTBOUND_WEBHOOK_URL")
    # Optional — if set, every outbound webhook is signed with HMAC-SHA256
    # in the X-Kora-Signature header so the receiver can verify it came
    # from us.
    OUTBOUND_WEBHOOK_SECRET = os.getenv("OUTBOUND_WEBHOOK_SECRET")

    # ---------- QuickBooks (quote -> Estimate) ----------
    # "simulated" (default) fabricates a plausible response, nothing leaves
    # the machine. "sandbox" makes real calls to Intuit's sandbox API and
    # needs all four vars below.
    QUICKBOOKS_MODE = os.getenv("QUICKBOOKS_MODE", "simulated").lower()
    QUICKBOOKS_CLIENT_ID = os.getenv("QUICKBOOKS_CLIENT_ID", "")
    QUICKBOOKS_CLIENT_SECRET = os.getenv("QUICKBOOKS_CLIENT_SECRET", "")
    QUICKBOOKS_REFRESH_TOKEN = os.getenv("QUICKBOOKS_REFRESH_TOKEN", "")
    QUICKBOOKS_REALM_ID = os.getenv("QUICKBOOKS_REALM_ID", "")