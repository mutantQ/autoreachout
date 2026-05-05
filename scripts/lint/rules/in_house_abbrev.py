"""Rule: ban configured in-house abbreviations in outbound message body zones.

Worked example: an internal acronym for a partner organization may read
naturally in private notes but feel jargon-y in conversational outbound
(SMS / KakaoTalk / email). Configure the forbidden tokens and their
suggested replacements in ``scripts/lint/_config.py``
(``IN_HOUSE_ABBREVIATIONS`` tuple). Set the tuple to empty to disable
the rule.

Body-zone scoping mirrors ``no_markdown_in_body``: only actual outbound
message text inside outbound section headers is scoped. Internal notes,
action items, blockquotes, metadata, and frontmatter remain free to
reference the abbreviation for historical context.

Scope:
- cold_contacts/*.md
- vendors/*.md
- Gmail MCP create_draft (subject + body + htmlBody)

Allowed exceptions:
- File contains the marker ``<!-- lint-disable in-house-abbrev -->``
- YAML frontmatter
- Blockquote lines (preserve quoted external text verbatim)
"""
import re
from pathlib import Path

from lint import Violation
from lint._config import IN_HOUSE_ABBREVIATIONS

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCOPED_PREFIXES = ("cold_contacts/", "vendors/")

# Build a single regex that matches any forbidden token. Forbidden tokens
# may contain ASCII hyphens; we expand each hyphen to match any Unicode
# dash variant. Empty tuple disables the rule entirely.
def _build_pattern() -> re.Pattern | None:
    if not IN_HOUSE_ABBREVIATIONS:
        return None
    parts = []
    for forbidden, _ in IN_HOUSE_ABBREVIATIONS:
        escaped = re.escape(forbidden)
        # Allow any unicode dash variant where the source uses ASCII '-'.
        escaped = escaped.replace(r"\-", r"[-‐-―]")
        parts.append(escaped)
    return re.compile("|".join(parts), re.IGNORECASE)


FORBIDDEN = _build_pattern()
SUGGESTIONS = {f.lower(): s for f, s in IN_HOUSE_ABBREVIATIONS}

BODY_HEADER_RE = re.compile(r"^###\s+Body\s*$", re.IGNORECASE)

OUTBOUND_SECTION_RE = re.compile(
    r"^##\s+(?:"
    r"Sent\b|"
    r"Outbound\s+draft\s+pending\s+review\b|"
    r"Reply\s+(?:received|sent)\b|"
    r"Follow[-\s]?up\s+sent\b|"
    r"Email\s+(?:sent|scheduled|draft)\b|"
    r"Confirmation\s+DM\s+sent\b|"
    r"SMS\s+(?:sent|draft)\b|"
    r"LinkedIn\s+(?:DM|message)\b|"
    r"In[-\s]?person\s+meeting\s+completed\b"
    r")",
    re.IGNORECASE,
)

POST_BODY_HEADERS = (
    "### Acceptance check",
    "### Reviewer attention flags",
    "### 사전 준비",
    "### 발송 후 체크리스트",
    "### Send pre-flight checklist",
    "### Open actions",
    "### Notes",
    "### Why this exists",
    "### 설계 의도",
    "### 통화 예상",
)

META_FIELD_RE = re.compile(r"^\*\*[^*]+:\*\*")


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


def _starts_post_body(stripped: str) -> bool:
    return any(stripped.startswith(h) for h in POST_BODY_HEADERS)


def _suggestion_for(token: str) -> str:
    return SUGGESTIONS.get(token.lower(), "(see scripts/lint/_config.py)")


def _scan_text(text: str, source: str) -> list[Violation]:
    if FORBIDDEN is None:
        return []
    if "<!-- lint-disable in-house-abbrev -->" in text:
        return []

    violations: list[Violation] = []
    lines = text.split("\n")
    in_frontmatter = False
    in_body = False
    pending_meta_skip = False

    for i, line in enumerate(lines, start=1):
        stripped = line.strip()

        if i == 1 and stripped == "---":
            in_frontmatter = True
            continue
        if in_frontmatter and stripped == "---":
            in_frontmatter = False
            continue
        if in_frontmatter:
            continue

        if BODY_HEADER_RE.match(stripped):
            in_body = True
            pending_meta_skip = False
            continue

        if _starts_post_body(stripped):
            in_body = False
            pending_meta_skip = False
            continue

        if OUTBOUND_SECTION_RE.match(stripped):
            in_body = True
            pending_meta_skip = True
            continue

        if stripped.startswith("## ") or stripped.startswith("### "):
            in_body = False
            pending_meta_skip = False
            continue

        if not in_body:
            continue

        if pending_meta_skip:
            if not stripped or META_FIELD_RE.match(stripped):
                continue
            pending_meta_skip = False

        if META_FIELD_RE.match(stripped):
            in_body = False
            continue

        if stripped.startswith(">"):
            continue

        for m in FORBIDDEN.finditer(line):
            token = m.group(0)
            context = stripped[:80]
            violations.append(Violation(
                rule="in-house-abbrev",
                file_path=source,
                line=i,
                message=(
                    f"{source}:{i} '{token}' (configured in-house abbreviation) "
                    f"inside outbound body zone reads as jargon. Context: "
                    f"\"{context}\". Suggested replacement: "
                    f"{_suggestion_for(token)}. Override per-file with "
                    f"<!-- lint-disable in-house-abbrev -->."
                ),
            ))

    return violations


def check(tool_name: str, tool_input: dict) -> list[Violation]:
    if FORBIDDEN is None:
        return []

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

    if tool_name == "mcp__claude_ai_Gmail__create_draft":
        for field in ("subject", "body", "htmlBody"):
            text = tool_input.get(field, "") or ""
            if text:
                violations.extend(_scan_gmail(text, f"Gmail.{field}"))

    return violations


def _scan_gmail(text: str, source: str) -> list[Violation]:
    """Scan Gmail draft fields. The entire content is body; no section-header
    scoping needed. Still respects blockquote and lint-disable marker."""
    if FORBIDDEN is None:
        return []
    if "<!-- lint-disable in-house-abbrev -->" in text:
        return []

    violations: list[Violation] = []
    for i, line in enumerate(text.split("\n"), start=1):
        stripped = line.strip()
        if stripped.startswith(">"):
            continue
        for m in FORBIDDEN.finditer(line):
            token = m.group(0)
            context = stripped[:80]
            violations.append(Violation(
                rule="in-house-abbrev",
                file_path=source,
                line=i,
                message=(
                    f"{source}:{i} '{token}' (configured in-house abbreviation) "
                    f"in outbound message reads as jargon. Context: "
                    f"\"{context}\". Suggested replacement: "
                    f"{_suggestion_for(token)}."
                ),
            ))
    return violations
