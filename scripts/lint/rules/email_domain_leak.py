"""Rule: never include FORBIDDEN_EMAIL in outbound message bodies.

Worked example: a founder with both a university email and a personal/work
email may want to keep the university email out of B2B outbound, since it
reads as "student" to enterprise recipients. Configure the forbidden and
preferred addresses in ``scripts/lint/_config.py``. Set
``FORBIDDEN_EMAIL = None`` to disable the rule.

Scope:
- cold_contacts/*.md (body, not frontmatter)
- drafts/*.md (body, not frontmatter)
- Gmail MCP create_draft body, subject, htmlBody
- Archive sections (## Sent, ## Reply, etc.) skipped — historical content
- vendors/*.md NOT in scope: vendor communications (law firms, contractors)
  may legitimately use any address in metadata logs

Allowed exceptions:
- YAML frontmatter ``email:`` field (recipients can have any address)
- File contains the marker ``<!-- lint-disable email-domain-leak -->``
"""
import re
from pathlib import Path

from lint import Violation, is_archive_section_header
from lint._config import FORBIDDEN_EMAIL, FOUNDER_EMAIL

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCOPED_PREFIXES = ("cold_contacts/", "drafts/")

LEAK_RE = re.compile(re.escape(FORBIDDEN_EMAIL), re.IGNORECASE) if FORBIDDEN_EMAIL else None


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
    return any(rel.startswith(prefix) for prefix in SCOPED_PREFIXES)


def _scan_text(text: str, source: str, skip_frontmatter: bool = True) -> list[Violation]:
    if LEAK_RE is None:
        return []
    if "<!-- lint-disable email-domain-leak -->" in text:
        return []

    lines = text.split("\n")
    in_frontmatter = False
    in_archive = False
    violations: list[Violation] = []

    for i, line in enumerate(lines, start=1):
        stripped = line.strip()
        if skip_frontmatter:
            if i == 1 and stripped == "---":
                in_frontmatter = True
                continue
            if in_frontmatter and stripped == "---":
                in_frontmatter = False
                continue
            if in_frontmatter:
                continue

        # Archive-section tracking (historical sent/received content).
        if is_archive_section_header(stripped):
            in_archive = True
            continue
        if stripped.startswith("## ") or stripped.startswith("# "):
            in_archive = False
        if in_archive:
            continue

        if LEAK_RE.search(line):
            violations.append(Violation(
                rule="email-domain-leak",
                file_path=source,
                line=i,
                severity="block",
                message=(
                    f"{source}:{i} {FORBIDDEN_EMAIL} appears in outbound body. "
                    f"Configured as forbidden in scripts/lint/_config.py. "
                    f"Use {FOUNDER_EMAIL} in outreach signoffs instead."
                ),
            ))
    return violations


def check(tool_name: str, tool_input: dict) -> list[Violation]:
    if LEAK_RE is None:
        return []

    violations: list[Violation] = []

    file_path = tool_input.get("file_path", "") or ""
    if file_path and _is_in_scope(file_path):
        rel = _relpath(file_path)
        for field in ("content", "new_string"):
            text = tool_input.get(field, "") or ""
            if text:
                violations.extend(_scan_text(text, rel, skip_frontmatter=True))
        for edit in tool_input.get("edits", []) or []:
            ns = edit.get("new_string", "") or ""
            if ns:
                violations.extend(_scan_text(ns, rel, skip_frontmatter=True))

    if tool_name == "mcp__claude_ai_Gmail__create_draft":
        for field in ("subject", "body", "htmlBody"):
            text = tool_input.get(field, "") or ""
            if text:
                violations.extend(_scan_text(text, f"Gmail.{field}", skip_frontmatter=False))

    return violations
