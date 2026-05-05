"""Project-specific identifiers used by lint rules. EDIT BEFORE USE.

Replace each value with your project's identifiers, or set to ``None`` to
disable the corresponding rule. Most lint rules import from this module so
that no PII or company-specific strings are hardcoded inside individual
rule files.

This is the single editable surface for adapting the harness to a new
project. Re-run ``pytest scripts/lint/tests/`` after changes.
"""

# ---------------------------------------------------------------------------
# Founder / sender identity
# ---------------------------------------------------------------------------

# Founder display name as it should appear in outbound signoffs.
# Used by: language_signoff, outbound_draft_channel_mismatch.
FOUNDER_NAME = "Founder"

# Email used in outbound mail. Used by email_domain_leak as the suggested
# replacement when FORBIDDEN_EMAIL slips into a body.
FOUNDER_EMAIL = "founder@acme.example"

# Email that must never appear in outbound bodies (e.g. an academic email
# that reads as "student" to enterprise recipients). Set to ``None`` to
# disable the email-domain-leak rule. The default placeholder lets the
# bundled tests run; replace it with your real forbidden address or set
# it to ``None`` once you have configured the harness for your project.
FORBIDDEN_EMAIL: str | None = "founder@university.edu"


# ---------------------------------------------------------------------------
# Project / company identity
# ---------------------------------------------------------------------------

# Project / company name as it should appear in signoffs. Used by
# language_signoff to detect Korean-body + English-only signoff drift.
COMPANY_NAME = "Acme"

# Primary-entity tag used in ``related_to:`` frontmatter to partition
# project-related contacts from personal-network contacts. Used by
# scripts/analyze.py to compute project-only engagement metrics.
PRIMARY_ENTITY = "acme"

# Project-owned domains that must include the ``https://`` prefix when
# referenced in outbound bodies (so they render as clickable links).
# Used by link_prefix_https. Set to an empty tuple to disable. The
# default keeps both the bundled-data domain (acme.example, RFC 2606
# reserved) and the test-fixture domains (example.com, demo.example.org)
# so a fresh checkout passes both lint and tests.
KNOWN_DOMAINS: tuple[str, ...] = ("acme.example", "example.com", "demo.example.org")


# ---------------------------------------------------------------------------
# Domain-specific abbreviation rule (worked example)
# ---------------------------------------------------------------------------

# Optional: in-house abbreviations that read naturally in internal notes
# but feel jargon-y in conversational outbound (SMS / KakaoTalk / email
# bodies). Each tuple is (forbidden_token, suggested_replacement). The
# in_house_abbrev rule uses this list verbatim. Set to an empty tuple
# to disable.
#
# Worked example: an internal acronym for a partner organization may
# read fine in your private notes but break tone in a Korean SMS where
# the recipient expects natural prose. Configure one entry per
# abbreviation; the tuple form keeps the suggested replacement next to
# the forbidden token.
IN_HOUSE_ABBREVIATIONS: tuple[tuple[str, str], ...] = (
    # ("PFC", "the center / Partner Forensic Center"),
)
