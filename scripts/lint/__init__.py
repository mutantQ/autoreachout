"""Outreach lint framework.

Each rule lives in scripts/lint/rules/{rule}.py and exports a `check(tool_name, tool_input) -> list[Violation]` function. The entry point is `scripts/lint/run_lint.py`, invoked as a PreToolUse hook.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class Violation:
    rule: str
    message: str
    file_path: Optional[str] = None
    line: Optional[int] = None
    severity: str = "block"  # "block" exits non-zero; "warn" prints but allows


# Section headers that mark HISTORICAL content (already sent, received, or
# logged). Rules that prevent leaks in OUTBOUND drafts should skip lines
# inside these sections — they're records, not future risk.
#
# Active draft sections like `## Outbound draft pending review (...)` are
# intentionally NOT in this list — those represent work in progress and
# must be scanned.
ARCHIVE_SECTION_PREFIXES = (
    "## Sent",
    "## Reply",
    "## Email sent",
    "## Email scheduled",
    "## Email draft",
    "## Follow-up",
    "## Follow up",
    "## Followup",
    "## LinkedIn DM",
    "## LinkedIn message",
    "## Call completed",
    "## Meeting",
    "## Withdrawn",
    "## Skipped",
    "## Retroactive",
    "## Thread",
    "## Response",
)


def is_archive_section_header(stripped_line: str) -> bool:
    """True if a stripped line opens a historical-content section."""
    return any(stripped_line.startswith(p) for p in ARCHIVE_SECTION_PREFIXES)
