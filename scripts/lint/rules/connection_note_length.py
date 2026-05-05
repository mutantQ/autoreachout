"""Rule: LinkedIn connection notes must be ≤300 characters.

LinkedIn enforces a 300-char limit on connection-note bodies.
Drafts longer than that either get truncated or rejected when sent.

Scope:
- cold_contacts/*.md
- drafts/*.md

Sections checked (heading prefix match, case-sensitive):
- `## Sent (connection note...`
- `## Outbound draft pending review...`

Body of each section is concatenated (excluding leading/trailing blank
lines) and counted as Python `len(str)`. Emoji and CJK count as 1 char
each — this is a close approximation of LinkedIn's count.

Allowed exceptions:
- File contains the marker `<!-- lint-disable connection-note-length -->`
"""
from pathlib import Path

from lint import Violation

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCOPED_PREFIXES = ("cold_contacts/", "drafts/")

LIMIT = 300

SECTION_HEADER_PREFIXES = (
    "## Sent (connection note",
    "## Outbound draft pending review",
)


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


def _section_starts(stripped: str) -> bool:
    return any(stripped.startswith(h) for h in SECTION_HEADER_PREFIXES)


def _is_heading(stripped: str) -> bool:
    return stripped.startswith("#")


def _scan_text(text: str, source: str) -> list[Violation]:
    if "<!-- lint-disable connection-note-length -->" in text:
        return []

    lines = text.split("\n")
    violations: list[Violation] = []

    in_target = False
    header_text = ""
    header_line = 0
    body_lines: list[str] = []

    def _flush() -> None:
        nonlocal in_target, header_text, header_line, body_lines
        if not in_target:
            return
        # Trim leading/trailing blank lines.
        while body_lines and not body_lines[0].strip():
            body_lines.pop(0)
        while body_lines and not body_lines[-1].strip():
            body_lines.pop()
        body = "\n".join(body_lines)
        count = len(body)
        if count > LIMIT:
            violations.append(Violation(
                rule="connection-note-length",
                file_path=source,
                line=header_line,
                severity="block",
                message=(
                    f"{source}:{header_line} '{header_text}' body is "
                    f"{count} chars, exceeds LinkedIn's {LIMIT}-char "
                    f"connection-note limit. Trim by {count - LIMIT} chars."
                ),
            ))
        in_target = False
        header_text = ""
        header_line = 0
        body_lines = []

    for i, line in enumerate(lines, start=1):
        stripped = line.strip()
        if _section_starts(stripped):
            _flush()
            in_target = True
            header_text = stripped
            header_line = i
            body_lines = []
            continue
        if in_target and _is_heading(stripped):
            _flush()
            continue
        if in_target:
            body_lines.append(line)
    _flush()

    return violations


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
