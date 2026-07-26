"""
Application-wide constants.
"""

# ===================================================
# CLIENTS
# ===================================================

CLIENT_STATUSES = (
    "lead",
    "contacted",
    "proposal_sent",
    "won",
    "lost",
    "active_client",
)


CLIENT_SOURCES = (
    "referral",
    "inbound_form",
    "cold_outreach",
    "social_media",
    "website",
)


# ===================================================
# CALL RECORDS
# ===================================================

CALL_TYPES = (
    "discovery",
    "internal",
    "follow_up",
    "negotiation",
    "kickoff",
)


PLATFORMS = (
    "Zoom",
    "Google Meet",
    "Microsoft Teams",
    "Phone",
)


# ===================================================
# PROPOSALS
# ===================================================

PROPOSAL_STATUSES = (
    "draft",
    "sent",
    "revised",
    "accepted",
    "rejected",
)


PROPOSAL_GENERATED_BY = (
    "AI",
    "Human",
)


# Business outcome of the deal — distinct from `status`, which only tracks
# the document's own lifecycle (draft/sent/revised/accepted/rejected).
PROPOSAL_OUTCOMES = (
    "pending",
    "won",
    "lost",
)


# ===================================================
# QUOTES
# ===================================================

QUOTE_STATUSES = (
    "draft",
    "sent",
    "accepted",
    "expired",
)


# ===================================================
# TEAM
# ===================================================

ROLE_CATEGORIES = (
    "Creative",
    "Production",
    "Operations",
    "Management",
)


# ===================================================
# DEFAULTS
# ===================================================

DEFAULT_PAGE = 1
DEFAULT_LIMIT = 20
MAX_LIMIT = 100
DEFAULT_LANGUAGE = "en-KE"