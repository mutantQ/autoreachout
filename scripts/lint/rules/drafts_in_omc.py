"""Rule: outbound message drafts must not live under `.omc/`.

All outbound drafts go in the canonical per-entity file at
`cold_contacts/{slug}.md` or `vendors/{slug}.md`. The single legitimate scratch location is
`outreach/drafts/{slug}.md` for entities not yet cold-contacted (enforced
by `one_file_per_entity.py`).

This rule complements `one_file_per_entity` by blocking outbound drafts
that get written to `.omc/` subdirectories (e.g.,
`.omc/team-{date}/drafts/`, `.omc/research/`, `.omc/specs/`,
`.omc/plans/`). Strategy / research / spec docs in `.omc/` are fine; only
files containing outbound-message markers are blocked.

Worked example of the failure mode: a parallel-worker session wrote
5 of 8 outbound message drafts to `.omc/team-batch/drafts/` instead
of per-entity `cold_contacts/{slug}.md` files. A subsequent attempt
to write a vendor brief to `.omc/team-batch/drafts/09-vendor-...md`
instead of appending to `vendors/{vendor}.md` was caught before the
file was created.

Scope:
- `.omc/**/*.md` (any markdown file under `.omc/`).

Allowed exceptions:
- File contains the marker `<!-- lint-disable drafts-in-omc -->`.
- File body lacks outbound-message markers (strategy / research / spec
  docs do not have `## Outbound draft pending review` headers nor the
  `**To:** ... + **Subject:** / **Channel:** ...` metadata block, so
  they pass through automatically).
"""
import re
from pathlib import Path

from lint import Violation

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCOPED_PREFIXES = (".omc/",)

# An outbound draft is recognized by either of the following content patterns.
# Both are deliberately strict (line-anchored, exact phrasing) to avoid
# false positives on summaries that mention drafts in tables or prose.
OUTBOUND_HEADER_RE = re.compile(
    r"^##\s+Outbound\s+draft\s+pending\s+review\b",
    re.MULTILINE,
)
TO_MARKER_RE = re.compile(r"^\*\*To:\*\*\s+\S", re.MULTILINE)
SUBJECT_MARKER_RE = re.compile(r"^\*\*Subject:\*\*\s+\S", re.MULTILINE)
CHANNEL_MARKER_RE = re.compile(r"^\*\*Channel:\*\*\s+\S", re.MULTILINE)


def _relpath(file_path: str) -> str:
    if not file_path:
        return ""
    p = str(file_path)
    root = str(PROJECT_ROOT) + "/"
    if p.startswith(root):
        return p[len(root):]
    return p


def _is_in_scope(file_path: str) -> bool:
    rel = _relpath(file_path)
    if not rel:
        return False
    return any(rel.startswith(prefix) for prefix in SCOPED_PREFIXES)


def _has_outbound_markers(text: str) -> bool:
    if OUTBOUND_HEADER_RE.search(text):
        return True
    has_to = bool(TO_MARKER_RE.search(text))
    has_subject_or_channel = bool(
        SUBJECT_MARKER_RE.search(text) or CHANNEL_MARKER_RE.search(text)
    )
    return has_to and has_subject_or_channel


def _scan_text(text: str, source: str) -> list[Violation]:
    if "<!-- lint-disable drafts-in-omc -->" in text:
        return []
    if not _has_outbound_markers(text):
        return []
    return [Violation(
        rule="drafts-in-omc",
        file_path=source,
        message=(
            f"{source} contains outbound-message draft markers but lives "
            f"under .omc/. Outbound drafts must go in "
            f"cold_contacts/{{slug}}.md "
            f"(existing contacts) or vendors/{{slug}}.md (vendors), as a "
            f"new ## section in the canonical per-entity file. Use "
            f"outreach/drafts/{{slug}}.md only for not-yet-cold-contact "
            f"entities. If this file is intentionally an internal "
            f"strategy / research / spec doc that contains message-format "
            f"snippets as reference (not as a draft to send), add the "
            f"marker <!-- lint-disable drafts-in-omc --> at the top."
        ),
    )]


def check(tool_name: str, tool_input: dict) -> list[Violation]:
    violations: list[Violation] = []
    file_path = tool_input.get("file_path", "") or ""
    if file_path and _is_in_scope(file_path):
        rel = _relpath(file_path)
        for field in ("content", "new_string"):
            text = tool_input.get(field, "") or ""
            if text:
                violations.extend(_scan_text(text, rel))
        for edit in tool_input.get("edits", []) or []:
            ns = edit.get("new_string", "") or ""
            if ns:
                violations.extend(_scan_text(ns, rel))
    return violations
