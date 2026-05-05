"""Rule: no level-4+ Markdown headings in cold_contacts/ or vendors/ drafts.

Outbound drafts in `cold_contacts/*.md` and `vendors/*.md` use level-2
(`## Sent (date)`, `## Outbound draft pending review (date)`) for entry
sections and level-3 (`### Body`, `### Acceptance check`, `### Reviewer
attention flags`) for sub-sections. Level-4 (`####`) and deeper headings
inside an outbound draft body render as plain `####` text in pasted/sent
emails and break the prose flow.

Worked-example failure: a draft once used `#### 1. ...` through
`#### 5. ...` to break the body into 5 numbered sub-sections. The
convention is bold inline or plain numbered prose lines instead;
level-4 headings render as literal hash characters in pasted email.

Scope:
- cold_contacts/*.md
- vendors/*.md

Allowed exceptions:
- File contains the marker `<!-- lint-disable body-headings -->`.
- YAML frontmatter (between the first pair of `^---$` lines).
"""
import re
from pathlib import Path

from lint import Violation

HEADING_RE = re.compile(r"^####+\s")

SCOPED_PREFIXES = (
    "cold_contacts/",
    "vendors/",
)
PROJECT_ROOT = Path(__file__).resolve().parents[3]


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


def _scan_text(text: str, source: str) -> list[Violation]:
    violations: list[Violation] = []

    if "<!-- lint-disable body-headings -->" in text:
        return violations

    lines = text.split("\n")
    in_frontmatter = False

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

        if HEADING_RE.match(line):
            level = len(line) - len(line.lstrip("#"))
            context = stripped[:80]
            violations.append(Violation(
                rule="body-headings",
                file_path=source,
                line=i,
                message=(
                    f"{source}:{i} level-{level} Markdown heading not allowed "
                    f"in outbound drafts. Context: \"{context}\". "
                    f"Fix: use bold inline (`**1. point**`) or plain numbered "
                    f"prose. Override per-file with "
                    f"<!-- lint-disable body-headings -->."
                ),
            ))
    return violations


def check(tool_name: str, tool_input: dict) -> list[Violation]:
    violations: list[Violation] = []

    file_path = tool_input.get("file_path", "") or ""
    if file_path and _is_in_scope(file_path):
        for field in ("content", "new_string"):
            text = tool_input.get(field, "") or ""
            if text:
                violations.extend(_scan_text(text, _relpath(file_path)))
        for edit in tool_input.get("edits", []) or []:
            ns = edit.get("new_string", "") or ""
            if ns:
                violations.extend(_scan_text(ns, _relpath(file_path)))

    return violations
